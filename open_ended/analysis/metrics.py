#!/usr/bin/env python3
"""Divergence metrics for the open-ended experiment.

These tasks are underspecified or multi-file, so there is no single correct behavior.
For each condition x case over K runs we report:
  - validity      : fraction of runs whose outputs satisfy the task contract (acceptable)
  - distinct_behav: number of distinct behavioral fingerprints AMONG VALID runs
                    (>1 = the model diverged on the free choices — the headline signal)
  - behav_consist : share of runs equal to the modal behavioral fingerprint (1.0 = identical)
  - distinct_text : number of distinct source texts (context for how much the code varied)

Usage: python3 analysis/metrics.py [--results-root results]
"""
import argparse
import json
import math
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
with open(os.path.join(ROOT, "data", "cases.json")) as _f:
    CASES = json.load(_f)

CONDITIONS = [
    ("Option 1 (Claude Code orchestrates)", "option1_default"),
    ("Option 2 (code orchestrates)", "option2"),
]


def load_runs(cdir):
    runs = []
    if not os.path.isdir(cdir):
        return runs
    for fn in sorted(os.listdir(cdir)):
        if fn.endswith(".json"):
            try:
                with open(os.path.join(cdir, fn)) as fh:
                    runs.append(json.load(fh))
            except (json.JSONDecodeError, OSError):
                runs.append({"_error": "unreadable"})
    return runs


def behav_key(r):
    if not isinstance(r, dict) or "_error" in r or not r.get("valid"):
        return None  # invalid/errored runs don't count toward behavioral agreement
    return r.get("behavior_fingerprint")


def consistency(keys):
    if not keys:
        return 0.0
    n = len(keys)
    counts = Counter(k if k is not None else "INVALID" for k in keys)
    return max(counts.values()) / n


def analyze(cond_dir):
    per_case = {}
    for cid in CASES:
        runs = load_runs(os.path.join(cond_dir, cid))
        if not runs:
            continue
        n = len(runs)
        valid = [r for r in runs if isinstance(r, dict) and "_error" not in r and r.get("valid")]
        distinct_behav = len({behav_key(r) for r in valid})
        distinct_text = len({r.get("source_sha256") for r in runs if isinstance(r, dict) and "_error" not in r})
        bkeys = [behav_key(r) for r in runs]
        per_case[cid] = dict(
            n=n, mode=CASES[cid]["mode"], validity=len(valid) / n,
            distinct_behav=distinct_behav, behav_consist=consistency(bkeys),
            distinct_text=distinct_text,
        )
    return per_case


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", default=os.path.join(ROOT, "results"))
    args = ap.parse_args()

    summary = []
    for label, sub in CONDITIONS:
        pc = analyze(os.path.join(args.results_root, sub))
        if not pc:
            print(f"\n### {label}\n  (no results in {os.path.join(args.results_root, sub)})")
            continue
        print(f"\n### {label}")
        print(f"  {'case':<16} {'mode':<24} {'N':>3} {'validity':>8} {'distinct_behav':>15} {'behav_consist':>14} {'distinct_text':>13}")
        for cid, d in pc.items():
            print(f"  {cid:<16} {d['mode']:<24} {d['n']:>3} {d['validity']:>8.2f} "
                  f"{d['distinct_behav']:>15} {d['behav_consist']:>14.2f} {d['distinct_text']:>13}")
        summary.append((label, pc))

    if len(summary) >= 2:
        print("\n" + "=" * 78)
        print("COMPARISON — distinct behaviors among valid runs (>1 = the model diverged)")
        print("=" * 78)
        cases = list(CASES.keys())
        print(f"  {'case':<16} {'mode':<24} " + "  ".join(lbl.split()[1] for lbl, _ in summary))
        for cid in cases:
            cells = []
            for _, pc in summary:
                d = pc.get(cid)
                cells.append("-" if not d else f"{d['distinct_behav']}@{d['behav_consist']:.2f}")
            print(f"  {cid:<16} {CASES[cid]['mode']:<24} " + "   ".join(f"{c:>10}" for c in cells))
        print("\n  cell = <distinct behaviors among valid runs>@<modal behavioral consistency>")
        print("  underspecified tasks: distinct>1 means runs made different valid choices.")
        print("  multifile_specified (m2_roman) is the control: one correct behavior, expect 1@1.00.")


if __name__ == "__main__":
    main()
