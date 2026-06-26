#!/usr/bin/env python3
"""Option 2 — code orchestrates, for the open-ended experiment.

The LLM is called only to generate the solution file(s); deterministic code writes
them, runs the divergence oracle, and (bounded) re-prompts on contract failure. The
model emits each file as a fenced block preceded by `### FILE: <name>` so multi-file
solutions can be parsed; a single unmarked block is treated as the task's one file.

Usage:
  python3 option2/run_option2.py --check
  python3 option2/run_option2.py --reps 10 --workers 6 --out-dir <dir>
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
import run_tests  # noqa: E402
from common.llm_client import get_client, complete, get_model  # noqa: E402

DATA = os.path.join(ROOT, "data")
with open(os.path.join(DATA, "cases.json")) as _f:
    CASES = json.load(_f)
MAX_ATTEMPTS = 3

_FILE_RE = re.compile(r"###\s*FILE:\s*([^\n`]+?)\s*\n```(?:python)?\s*\n(.*?)```", re.DOTALL)
_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def load_spec(case_id):
    with open(os.path.join(DATA, "specs", f"{case_id}.md")) as fh:
        return fh.read()


def parse_files(text, required):
    """Return {filename: source}. Honor ### FILE: markers; else first block -> sole file."""
    found = {name.strip(): body.strip() + "\n" for name, body in _FILE_RE.findall(text)}
    if found:
        return found
    m = _BLOCK_RE.search(text)
    body = (m.group(1) if m else text).strip() + "\n"
    return {required[0]: body}


def llm_generate(client, spec_text, signature, required, feedback=None):
    sys_p = ("You write small, pure Python. Output ONLY the required file(s), each as a fenced "
             "```python block immediately preceded by a line `### FILE: <filename>`. No prose, "
             "no tests, no printing, no imports of os/sys/random/time/socket/subprocess.")
    user_p = (f"Entry: {signature}\nRequired files: {', '.join(required)}\n"
              f"Use absolute imports between files (e.g. `from core import ...`).\n\n"
              f"SPECIFICATION:\n{spec_text}")
    if feedback:
        user_p += "\n\nYour previous attempt produced unacceptable outputs (fix them):\n" + feedback
    text, model = complete(client, sys_p, user_p, max_tokens=1500)
    return parse_files(text, required), model


def run_pipeline(client, case_id):
    meta = CASES[case_id]
    spec = load_spec(case_id)
    model_id = get_model()
    feedback, rec, attempts = None, None, 0
    with tempfile.TemporaryDirectory(prefix="oe2-") as tmp:
        for attempts in range(1, MAX_ATTEMPTS + 1):
            files, model_id = llm_generate(client, spec, meta["signature"], meta["files"], feedback)
            for fn in os.listdir(tmp):  # clear prior attempt
                os.remove(os.path.join(tmp, fn))
            for name, body in files.items():
                with open(os.path.join(tmp, os.path.basename(name)), "w") as fh:
                    fh.write(body)
            rec = run_tests.evaluate(case_id, tmp)
            if rec["valid"]:
                break
            fails = rec.get("_contract_failures", [])[:6]
            feedback = "\n".join(f"- input={i} -> {g}" for i, g in fails)
    rec["_model"] = model_id
    rec["_attempts"] = attempts
    rec.pop("_contract_failures", None)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--cases", nargs="*", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    client = get_client()
    cases = args.cases or list(CASES.keys())

    if args.check:
        ok = True
        for cid in cases:
            rec = run_pipeline(client, cid)
            v = "VALID" if rec["valid"] else f"INVALID/{rec['status']}"
            print(f"[check] {cid} model={rec['_model']} attempts={rec['_attempts']} -> {v} "
                  f"fp={(rec['behavior_fingerprint'] or 'none')[:10]}")
            ok = ok and rec["valid"]
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
        if rec.get("files"):  # persist generated source dir for inspection
            sdir = os.path.join(cdir, f"run_{i:03d}.solution")
            os.makedirs(sdir, exist_ok=True)
            for name, body in rec["files"].items():
                with open(os.path.join(sdir, os.path.basename(name)), "w") as fh:
                    fh.write(body)
        verdict = "ERROR" if "_error" in rec else ("valid" if rec["valid"] else f"INVALID/{rec['status']}")
        return cid, i, verdict

    jobs = [(cid, i) for cid in cases for i in range(args.reps)]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for cid, i, verdict in pool.map(lambda a: one_run(*a), jobs):
            print(f"[{cid}] rep {i} -> {verdict}")
    print(f"Option 2 done -> {out_dir}")


if __name__ == "__main__":
    main()
