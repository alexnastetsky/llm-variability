#!/usr/bin/env python3
"""Assemble the graded run JSON from a final solution file + the behavioral oracle.

Used by Option 1's run_one.sh AFTER `claude -p` finishes: the harness (not the
model) runs the oracle on the model's final solution and writes the authoritative
graded record, so behavior is captured by the harness rather than self-reported.

Usage: python3 tools/record_run.py <case_id> <solution_path> <out_path> [--model M] [--attempts N]
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_tests  # noqa: E402


def build_record(case_id, solution_path, model=None, attempts=None, variant=None):
    if not os.path.exists(solution_path):
        return {"_error": "no-solution", "case_id": case_id, "_variant": variant}
    rec = run_tests.evaluate(case_id, solution_path)
    return {
        "case_id": case_id,
        "func_name": rec["func_name"],
        "source": rec["source"],
        "source_sha256": rec["source_sha256"],
        "structural_sha256": rec["structural_sha256"],
        "behavior": rec["behavior"],
        "behavior_sha256": rec["behavior_sha256"],
        "correct": rec["correct"],
        "_model": model,
        "_valid": rec["passed_named"],
        "_attempts": attempts,
        "_variant": variant,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case_id")
    ap.add_argument("solution_path")
    ap.add_argument("out_path")
    ap.add_argument("--model", default=None)
    ap.add_argument("--attempts", type=int, default=None)
    ap.add_argument("--variant", default=None)
    args = ap.parse_args()
    rec = build_record(args.case_id, args.solution_path, args.model, args.attempts, args.variant)
    os.makedirs(os.path.dirname(os.path.abspath(args.out_path)), exist_ok=True)
    with open(args.out_path, "w") as fh:
        json.dump(rec, fh, indent=2)
    verdict = "no-solution" if "_error" in rec else ("correct" if rec["correct"] else
              ("valid" if rec["_valid"] else "INVALID"))
    print(f"[{args.case_id}] {os.path.basename(args.out_path)} -> {verdict}")


if __name__ == "__main__":
    main()
