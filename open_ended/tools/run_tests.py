#!/usr/bin/env python3
"""Divergence oracle for the open-ended experiment.

Unlike the codegen oracle (which matches a single hidden reference), these tasks are
underspecified or multi-file: there may be MANY acceptable behaviors. So this oracle
grades each run two ways:
  - validity   : do the candidate's outputs satisfy the task CONTRACT on every corpus
                 input? (a permissive checker for "acceptable", in data/contracts/<case>.py)
  - behavior   : a fingerprint = hash of the candidate's output vector over the fixed
                 seeded corpus. Runs with the SAME fingerprint chose the same behavior;
                 DIFFERENT fingerprints = the runs diverged on the free choices.
The headline metric (analysis/metrics.py) is how many distinct fingerprints appear
across runs — i.e. whether the model converges or diverges when the spec leaves room.

A candidate solution is a DIRECTORY of one or more .py files; the entry module/function
come from data/cases.json. evaluate() runs the candidate in an isolated subprocess.

  evaluate(case_id, solution_dir) -> dict
  CLI:  python3 tools/run_tests.py <case_id> <solution_dir>   -> VALID / INVALID
  python3 tools/run_tests.py --selftest                       -> every reference is VALID
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

sys.path.insert(0, HERE)
import corpus  # noqa: E402

with open(os.path.join(DATA, "cases.json")) as _f:
    CASES = json.load(_f)

IMPORT_ALLOWLIST = {"typing", "math", "collections", "itertools", "functools", "re", "string", "statistics"}
BANNED_NAMES = {"open", "eval", "exec", "compile", "__import__", "input", "exit", "quit"}


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def static_precheck(source, local_modules):
    """None if safe to run, else a reason. Local (sibling) modules are allowed imports."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return f"syntax_error: {e.msg}"
    allowed = IMPORT_ALLOWLIST | set(local_modules)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in allowed:
                    return f"disallowed_import: {a.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and (node.module or "").split(".")[0] not in allowed:
                return f"disallowed_import: {node.module}"
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            return f"banned_name: {node.id}"
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return f"banned_dunder_attr: {node.attr}"
    return None


def structural_source(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
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


def _set_limits():
    for lim, val in [(resource.RLIMIT_CPU, (4, 5)), (resource.RLIMIT_FSIZE, (0, 0))]:
        try:
            resource.setrlimit(lim, val)
        except (ValueError, OSError):
            pass
    if platform.system() != "Darwin":
        try:
            resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
        except (ValueError, OSError):
            pass


def _run_inputs(sol_dir, entry, func_name, inputs, timeout_s):
    with tempfile.TemporaryDirectory(prefix="oe-run-") as tmp:
        inputs_path = os.path.join(tmp, "inputs.json")
        with open(inputs_path, "w") as fh:
            json.dump({"inputs": inputs}, fh)
        env = {"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1", "PATH": os.environ.get("PATH", "")}
        try:
            proc = subprocess.run(
                [sys.executable, "-B", RUNNER, os.path.abspath(sol_dir), entry, func_name, inputs_path],
                cwd=tmp, env=env, capture_output=True, text=True, timeout=timeout_s, preexec_fn=_set_limits,
            )
        except subprocess.TimeoutExpired:
            return "timeout", None
        if proc.returncode != 0:
            return "runtime_error_global", None
        try:
            return "ok", json.loads(proc.stdout)["results"]
        except (json.JSONDecodeError, KeyError):
            return "runtime_error_global", None


def _load_contract(case_id):
    spec = importlib.util.spec_from_file_location("c_" + case_id, os.path.join(DATA, "contracts", f"{case_id}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.check


def _read_solution(solution_dir, required):
    files = {}
    missing = []
    for fn in required:
        p = os.path.join(solution_dir, fn)
        if os.path.exists(p):
            with open(p) as fh:
                files[fn] = fh.read()
        else:
            missing.append(fn)
    return files, missing


def evaluate(case_id, solution_dir, timeout_s=None):
    meta = CASES[case_id]
    timeout_s = timeout_s or meta.get("timeout_s", 5.0)
    files, missing = _read_solution(solution_dir, meta["files"])
    text_sha = _sha(json.dumps({k: files[k] for k in sorted(files)}, sort_keys=True))
    struct_sha = _sha(json.dumps({k: structural_source(files[k]) for k in sorted(files)}, sort_keys=True))
    base = {"case_id": case_id, "mode": meta["mode"], "files": files,
            "source_sha256": text_sha, "structural_sha256": struct_sha}

    def done(status, fingerprint, n_valid, valid, failures):
        return {**base, "status": status, "behavior_fingerprint": fingerprint,
                "n_corpus": meta["n_corpus"], "n_valid": n_valid, "valid": valid,
                "_contract_failures": failures}

    if missing:
        return done("missing_files", None, 0, False, [(f"missing: {missing}", "")])

    local_modules = {os.path.splitext(fn)[0] for fn in meta["files"]}
    for fn, src in files.items():
        reason = static_precheck(src, local_modules)
        if reason is not None:
            return done("blocked", None, 0, False, [(f"{fn}: {reason}", "")])

    corpus_args = corpus.corpus_inputs(case_id)
    status, results = _run_inputs(solution_dir, meta["entry"], meta["func_name"], corpus_args, timeout_s)
    if status != "ok":
        return done(status, None, 0, False, [("<all>", status)])

    check = _load_contract(case_id)
    n_valid, failures = 0, []
    for args, res in zip(corpus_args, results):
        ok = False
        if "v" in res:
            try:
                ok = bool(check(args, json.loads(res["v"])))
            except Exception:  # noqa: BLE001
                ok = False
        if ok:
            n_valid += 1
        elif len(failures) < 6:
            got = res.get("v", f"raises {res.get('e')}")
            failures.append((repr(args), got))
    fingerprint = _sha(json.dumps(results, sort_keys=True))
    all_valid = (n_valid == len(results))
    return done("ok", fingerprint, n_valid, all_valid, failures)


# --------------------------------------------------------------------------- CLI
def _cli_one(case_id, solution_dir):
    rec = evaluate(case_id, solution_dir)
    if rec["valid"]:
        print(f"VALID (contract holds on {rec['n_valid']}/{rec['n_corpus']} corpus inputs)")
        return 0
    lines = [f"INVALID (status={rec['status']}, contract holds on {rec['n_valid']}/{rec['n_corpus']})"]
    for inp, got in rec["_contract_failures"][:6]:
        lines.append(f"  input={inp}  unacceptable output={got}")
    print("\n".join(lines))
    return 1


def _selftest():
    ok = True
    for cid in CASES:
        ref = os.path.join(DATA, "reference", cid)
        rec = evaluate(cid, ref)
        print(f"[selftest] {cid} ({rec['mode']}): status={rec['status']} valid={rec['valid']} "
              f"({rec['n_valid']}/{rec['n_corpus']})")
        ok = ok and rec["valid"]
    print("SELFTEST OK" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case_id", nargs="?")
    ap.add_argument("solution_dir", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(_selftest())
    if not (args.case_id and args.solution_dir):
        ap.error("provide <case_id> <solution_dir>, or --selftest")
    sys.exit(_cli_one(args.case_id, args.solution_dir))


if __name__ == "__main__":
    main()
