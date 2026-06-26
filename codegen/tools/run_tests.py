#!/usr/bin/env python3
"""Behavioral oracle for the codegen experiment (analogue of validate_json.py).

Compiles + runs a candidate solution in an isolated, resource-limited subprocess
against (a) the named test suite (the "shown" oracle) and (b) a fixed seeded
differential-testing corpus compared against the reference solution (the "hidden"
oracle). Produces a behavioral record; never executes candidate code in-process.

Roles:
  - evaluate(case_id, solution_path) -> dict   (importable; used by both options + analysis)
  - CLI:  python3 tools/run_tests.py <case_id> <solution_path>   -> PASS / FAIL (named tests only)
  - python3 tools/run_tests.py --build-cache   (cache reference corpus vectors)
  - python3 tools/run_tests.py --selftest      (every reference must PASS its own oracle)

Safety: a static AST pre-check refuses to run code that imports outside a small
pure-stdlib allowlist or calls open/eval/exec/compile/__import__/input; the
subprocess sets RLIMIT_CPU / RLIMIT_FSIZE (and RLIMIT_AS off macOS), a wall-clock
timeout, PYTHONHASHSEED=0, -B (no bytecode), and cwd in a temp dir with no data/.
Network is NOT hard-blocked by stdlib alone (documented limitation); tasks are pure.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
import platform
import resource
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
RUNNER = os.path.join(HERE, "_runner.py")
DATA = os.path.join(ROOT, "data")
CACHE_DIR = os.path.join(HERE, ".corpus_cache")

sys.path.insert(0, HERE)
import corpus  # noqa: E402  (tools/corpus.py)

with open(os.path.join(DATA, "cases.json")) as _f:
    CASES = json.load(_f)

# Imports a pure candidate may legitimately use; anything else is refused.
IMPORT_ALLOWLIST = {"typing", "math", "collections", "itertools", "functools", "re", "string"}
BANNED_NAMES = {"open", "eval", "exec", "compile", "__import__", "input", "exit", "quit"}


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- static safety
def static_precheck(source):
    """Return None if safe to run, else a short reason string."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return f"syntax_error: {e.msg}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in IMPORT_ALLOWLIST:
                    return f"disallowed_import: {a.name}"
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in IMPORT_ALLOWLIST:
                return f"disallowed_import: {node.module}"
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            return f"banned_name: {node.id}"
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return f"banned_dunder_attr: {node.attr}"
    return None


# ----------------------------------------------------------- structural identity
def structural_source(source):
    """Comment/docstring/format-insensitive normalization of source (stdlib only)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source  # fall back to raw; text altitude still distinguishes it
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) \
                and body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
    try:
        return ast.unparse(ast.fix_missing_locations(tree))
    except Exception:  # noqa: BLE001
        return source


# ------------------------------------------------------------- subprocess limits
def _set_limits():  # runs in the child, before exec
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (4, 5))
    except (ValueError, OSError):
        pass
    try:
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))  # no file writes
    except (ValueError, OSError):
        pass
    if platform.system() != "Darwin":  # RLIMIT_AS is unreliable / harmful on macOS
        try:
            resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
        except (ValueError, OSError):
            pass


def _run_inputs(solution_path, func_name, inputs, timeout_s):
    """Run the candidate over inputs in a subprocess. Returns (status, results|None)."""
    with tempfile.TemporaryDirectory(prefix="codegen-run-") as tmp:
        inputs_path = os.path.join(tmp, "inputs.json")
        with open(inputs_path, "w") as fh:
            json.dump({"inputs": inputs}, fh)
        env = {"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1",
               "PATH": os.environ.get("PATH", "")}
        try:
            proc = subprocess.run(
                [sys.executable, "-B", RUNNER, os.path.abspath(solution_path), func_name, inputs_path],
                cwd=tmp, env=env, capture_output=True, text=True,
                timeout=timeout_s, preexec_fn=_set_limits,
            )
        except subprocess.TimeoutExpired:
            return "timeout", None
        if proc.returncode != 0:
            return "runtime_error_global", None
        try:
            return "ok", json.loads(proc.stdout)["results"]
        except (json.JSONDecodeError, KeyError):
            return "runtime_error_global", None


# ----------------------------------------------------------------- reference cache
def _named(case_id):
    spec = importlib.util.spec_from_file_location("t_" + case_id, os.path.join(DATA, "tests", f"{case_id}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.TESTS  # list of (args_tuple, expected)


def _canon_value(value):
    return json.dumps(value, sort_keys=True, default=repr)


def reference_corpus(case_id, timeout_s):
    """Cached reference behavior over the corpus: (results_list, sha256)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{case_id}.json")
    if os.path.exists(cache_path):
        with open(cache_path) as fh:
            c = json.load(fh)
        return c["results"], c["sha256"]
    ref_path = os.path.join(DATA, "reference", f"{case_id}.py")
    status, results = _run_inputs(ref_path, CASES[case_id]["func_name"], corpus.corpus_inputs(case_id), timeout_s)
    if status != "ok":
        raise RuntimeError(f"reference for {case_id} failed to run cleanly: {status}")
    sha = _sha(json.dumps(results, sort_keys=True))
    with open(cache_path, "w") as fh:
        json.dump({"results": results, "sha256": sha}, fh)
    return results, sha


# ----------------------------------------------------------------------- evaluate
def evaluate(case_id, solution_path, timeout_s=None):
    """Compile + run a candidate against named tests and the differential corpus."""
    meta = CASES[case_id]
    func_name = meta["func_name"]
    timeout_s = timeout_s or meta.get("timeout_s", 5.0)
    named = _named(case_id)
    named_args = [list(args) for args, _ in named]
    named_expected = [exp for _, exp in named]
    corpus_args = corpus.corpus_inputs(case_id)

    with open(solution_path) as fh:
        source = fh.read()

    base = {
        "func_name": func_name, "source": source, "source_sha256": _sha(source),
        "structural_sha256": _sha(structural_source(source)),
        "n_tests": len(named), "n_corpus": len(corpus_args),
    }

    reason = static_precheck(source)
    if reason is not None:
        beh = {"status": "blocked", "reason": reason, "test_results": [False] * len(named),
               "corpus_vector_sha256": None, "n_tests": len(named), "n_tests_passed": 0,
               "n_corpus": len(corpus_args), "n_corpus_matched": 0, "matches_reference": False}
        return _finish(base, beh, named_failures=[("static-precheck", reason, "blocked")])

    status, results = _run_inputs(solution_path, func_name, named_args + corpus_args, timeout_s)
    if status != "ok":
        beh = {"status": status, "test_results": [False] * len(named), "corpus_vector_sha256": None,
               "n_tests": len(named), "n_tests_passed": 0, "n_corpus": len(corpus_args),
               "n_corpus_matched": 0, "matches_reference": False}
        return _finish(base, beh, named_failures=[("<all>", status, status)])

    named_results = results[:len(named)]
    corpus_results = results[len(named):]

    # named tests: pass iff value present and equals expected, OR (for a
    # {"__raises__": "ExcType"} sentinel) the run raised exactly that exception type.
    test_results, named_failures = [], []
    for i, (res, exp) in enumerate(zip(named_results, named_expected)):
        if isinstance(exp, dict) and "__raises__" in exp:
            want = exp["__raises__"]
            ok = res.get("e") == want
            exp_str = f"raises {want}"
        else:
            ok = ("v" in res) and (res["v"] == _canon_value(exp))
            exp_str = _canon_value(exp)
        test_results.append(ok)
        if not ok:
            got = res["v"] if "v" in res else f"raises {res.get('e')}"
            named_failures.append((repr(named_args[i]), exp_str, got))

    # corpus: elementwise equality vs cached reference vector
    ref_results, _ = reference_corpus(case_id, timeout_s)
    n_matched = sum(1 for a, b in zip(corpus_results, ref_results) if a == b)
    matches_reference = (n_matched == len(ref_results))
    corpus_sha = _sha(json.dumps(corpus_results, sort_keys=True))

    beh = {"status": "ok", "test_results": test_results, "corpus_vector_sha256": corpus_sha,
           "n_tests": len(named), "n_tests_passed": sum(test_results), "n_corpus": len(corpus_args),
           "n_corpus_matched": n_matched, "matches_reference": matches_reference}
    return _finish(base, beh, named_failures=named_failures)


def _finish(base, beh, named_failures):
    behavior_sha = _sha(json.dumps(
        {"status": beh["status"], "test_results": beh["test_results"],
         "corpus_vector_sha256": beh["corpus_vector_sha256"]}, sort_keys=True))
    passed = (beh["status"] == "ok") and (beh["n_tests_passed"] == beh["n_tests"])
    correct = passed and beh["matches_reference"]
    return {**base, "behavior": beh, "behavior_sha256": behavior_sha,
            "passed_named": passed, "correct": correct, "_named_failures": named_failures}


# --------------------------------------------------------------------------- CLI
def _cli_one(case_id, solution_path):
    rec = evaluate(case_id, solution_path)
    beh = rec["behavior"]
    if rec["passed_named"]:
        print(f"PASS ({beh['n_tests_passed']}/{beh['n_tests']} named tests)")
        return 0
    # reveal named failures only (never the corpus answer key)
    lines = [f"FAIL ({beh['n_tests_passed']}/{beh['n_tests']} named tests; status={beh['status']})"]
    for inp, exp, got in rec["_named_failures"][:10]:
        lines.append(f"  input={inp}  expected={exp}  got={got}")
    print("\n".join(lines))
    return 1


def _build_cache():
    for cid in CASES:
        results, sha = reference_corpus(cid, CASES[cid].get("timeout_s", 5.0))
        print(f"[cache] {cid}: {len(results)} corpus outputs, sha={sha[:12]}")
    return 0


def _selftest():
    ok = True
    for cid in CASES:
        ref = os.path.join(DATA, "reference", f"{cid}.py")
        rec = evaluate(cid, ref)
        b = rec["behavior"]
        verdict = "OK" if rec["correct"] else "FAIL"
        print(f"[selftest] {cid} {rec['func_name']}: tests {b['n_tests_passed']}/{b['n_tests']}, "
              f"corpus {b['n_corpus_matched']}/{b['n_corpus']} -> {verdict}")
        ok = ok and rec["correct"]
    print("SELFTEST OK" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case_id", nargs="?")
    ap.add_argument("solution_path", nargs="?")
    ap.add_argument("--build-cache", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.build_cache:
        sys.exit(_build_cache())
    if args.selftest:
        sys.exit(_selftest())
    if not (args.case_id and args.solution_path):
        ap.error("provide <case_id> <solution_path>, or --selftest / --build-cache")
    sys.exit(_cli_one(args.case_id, args.solution_path))


if __name__ == "__main__":
    main()
