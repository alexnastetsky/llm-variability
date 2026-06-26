#!/usr/bin/env python3
"""Build the graded run JSON from a candidate solution DIRECTORY + the divergence oracle.
Used by Option 1's run_one.sh after `claude -p` finishes (harness-authoritative grading).

Usage: python3 tools/record_run.py <case_id> <solution_dir> <out_path> [--model M] [--attempts N]
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_tests  # noqa: E402


def build_record(case_id, solution_dir, model=None, attempts=None):
    if not os.path.isdir(solution_dir) or not os.listdir(solution_dir):
        return {"_error": "no-solution", "case_id": case_id}
    rec = run_tests.evaluate(case_id, solution_dir)
    rec["_model"] = model
    rec["_attempts"] = attempts
    rec.pop("_contract_failures", None)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case_id")
    ap.add_argument("solution_dir")
    ap.add_argument("out_path")
    ap.add_argument("--model", default=None)
    ap.add_argument("--attempts", type=int, default=None)
    args = ap.parse_args()
    rec = build_record(args.case_id, args.solution_dir, args.model, args.attempts)
    os.makedirs(os.path.dirname(os.path.abspath(args.out_path)), exist_ok=True)
    with open(args.out_path, "w") as fh:
        json.dump(rec, fh, indent=2)
    verdict = "no-solution" if "_error" in rec else (
        "valid" if rec["valid"] else f"INVALID/{rec['status']}")
    fp = "" if "_error" in rec else f" fp={(rec['behavior_fingerprint'] or 'none')[:10]}"
    print(f"[{args.case_id}] {os.path.basename(args.out_path)} -> {verdict}{fp}")


if __name__ == "__main__":
    main()
