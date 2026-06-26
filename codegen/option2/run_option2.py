#!/usr/bin/env python3
"""Option 2 — code orchestrates. Deterministic harness for the codegen workload.

The ONLY cognitive sub-step delegated to the LLM is generating the function source.
Everything else — writing the file, running the behavioral oracle, the bounded
fix loop, and assembling the graded record — is deterministic Python. A bounded,
fixed-protocol fix loop (max_attempts) mirrors Option 1's validation loop so both
architectures iterate; the contrast is WHO drives the loop (fixed code vs the LLM),
not whether one exists.

Usage:
  python3 option2/run_option2.py --check
  python3 option2/run_option2.py --reps 20 --cases case01 case02 --workers 8 --out-dir <dir>
"""
import argparse
import json
import os
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import run_tests  # noqa: E402  (tools/run_tests.py)
from common.llm_client import get_client, complete, get_model  # noqa: E402

DATA = os.path.join(ROOT, "data")
with open(os.path.join(DATA, "cases.json")) as _f:
    CASES = json.load(_f)
MAX_ATTEMPTS = 3

_FENCE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)


def _extract_code(text):
    m = _FENCE.search(text)
    return (m.group(1) if m else text).strip() + "\n"


def load_spec(case_id):
    with open(os.path.join(DATA, "specs", f"{case_id}.md")) as fh:
        return fh.read()


def llm_generate(client, spec_text, signature, feedback=None):
    sys_p = ("You write a single pure Python function. Output ONLY a fenced ```python code "
             "block containing the function definition — no prose, no tests, no example calls, "
             "no printing, no imports of os/sys/random/time/socket/subprocess.")
    user_p = f"Implement exactly this function:\n  {signature}\n\nSPECIFICATION:\n{spec_text}"
    if feedback:
        user_p += ("\n\nYour previous attempt failed these tests (fix them):\n" + feedback)
    text, model = complete(client, sys_p, user_p, max_tokens=1024)
    return _extract_code(text), model


def run_pipeline(client, case_id):
    """Generate -> validate -> (bounded) fix loop. Returns the graded record dict."""
    meta = CASES[case_id]
    spec = load_spec(case_id)
    model_id = get_model()
    feedback = None
    rec = None
    attempts = 0
    with tempfile.TemporaryDirectory(prefix="opt2-") as tmp:
        sol_path = os.path.join(tmp, "solution.py")
        for attempts in range(1, MAX_ATTEMPTS + 1):
            source, model_id = llm_generate(client, spec, meta["signature"], feedback)
            with open(sol_path, "w") as fh:
                fh.write(source)
            rec = run_tests.evaluate(case_id, sol_path)
            if rec["passed_named"]:
                break
            # build deterministic feedback from named failures for the next attempt
            fails = rec.get("_named_failures", [])[:8]
            feedback = "\n".join(f"- input={i} expected={e} got={g}" for i, e, g in fails)
    return _assemble(case_id, rec, model_id, attempts)


def _assemble(case_id, rec, model_id, attempts):
    return {
        "case_id": case_id,
        "func_name": rec["func_name"],
        "source": rec["source"],
        "source_sha256": rec["source_sha256"],
        "structural_sha256": rec["structural_sha256"],
        "behavior": rec["behavior"],
        "behavior_sha256": rec["behavior_sha256"],
        "correct": rec["correct"],
        "_model": model_id,
        "_valid": rec["passed_named"],
        "_attempts": attempts,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=20)
    ap.add_argument("--cases", nargs="*", default=None, help="subset of case ids")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--workers", type=int, default=8, help="concurrent requests")
    ap.add_argument("--check", action="store_true",
                    help="one rep/case; assert correct behavior; print model id")
    args = ap.parse_args()

    client = get_client()
    run_tests.reference_corpus  # ensure module loaded
    for cid in CASES:  # warm reference cache (serial, before fan-out)
        run_tests.reference_corpus(cid, CASES[cid].get("timeout_s", 5.0))
    cases = args.cases or sorted(CASES.keys())

    if args.check:
        ok = True
        for cid in cases:
            rec = run_pipeline(client, cid)
            b = rec["behavior"]
            status = "OK" if rec["correct"] else f"NOT-CORRECT (tests {b['n_tests_passed']}/{b['n_tests']}, corpus {b['n_corpus_matched']}/{b['n_corpus']})"
            print(f"[check] {cid} model={rec['_model']} attempts={rec['_attempts']} -> {status}")
            ok = ok and rec["correct"]
        sys.exit(0 if ok else 1)

    out_dir = args.out_dir or os.path.join(ROOT, "results", "option2")

    def one_run(cid, i):
        try:
            rec = run_pipeline(client, cid)
        except Exception as e:  # noqa: BLE001
            rec = {"_error": f"{type(e).__name__}: {e}", "case_id": cid}
        cdir = os.path.join(out_dir, cid)
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, f"run_{i:03d}.json"), "w") as fh:
            json.dump(rec, fh, indent=2)
        verdict = "ERROR" if "_error" in rec else ("correct" if rec["correct"] else
                  ("valid" if rec["_valid"] else "INVALID"))
        return cid, i, verdict

    jobs = [(cid, i) for cid in cases for i in range(args.reps)]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for cid, i, verdict in pool.map(lambda a: one_run(*a), jobs):
            print(f"[{cid}] rep {i} -> {verdict}")
    print(f"Option 2 done -> {out_dir}")


if __name__ == "__main__":
    main()
