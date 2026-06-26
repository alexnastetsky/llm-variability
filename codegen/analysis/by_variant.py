#!/usr/bin/env python3
"""Per-prompt-variant behavioral breakdown, to confirm consistency isn't an artifact
of a single fixed prompt. For each condition, groups runs by (case, variant) and reports
behavioral consistency + correctness per variant, plus pooled-across-variants.

Usage: python3 analysis/by_variant.py [--results-root results]
"""
import argparse
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
from analysis.metrics import canonical, truth_behav, load_runs, _consistency, CONDITIONS  # noqa: E402
from analysis.ground_truth import gold_behavior  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", default=os.path.join(ROOT, "results"))
    args = ap.parse_args()
    gold = gold_behavior()

    for label, sub in CONDITIONS:
        cond_dir = os.path.join(args.results_root, sub)
        if not os.path.isdir(cond_dir):
            continue
        # (case, variant) -> list of (behav_key, correct)
        cell = defaultdict(list)
        for cid in sorted(gold):
            tcan = truth_behav(cid, gold)
            for r in load_runs(os.path.join(cond_dir, cid)):
                var = r.get("_variant", "?") if isinstance(r, dict) else "?"
                key = canonical(r, "behav") or ("INVALID",)
                cell[(cid, var)].append((key, key == tcan))
        if not cell:
            continue
        variants = sorted({v for _, v in cell})
        print(f"\n### {label}")
        print(f"  within-(case,variant) behavioral consistency, averaged over cases:")
        print(f"  {'variant':<8} {'cells':>6} {'N':>4} {'mean_behav_consist':>20} {'correct':>8}")
        for var in variants:
            rows = [cell[k] for k in cell if k[1] == var]
            consistencies = [_consistency([key for key, _ in cellrows])[0] for cellrows in rows]
            n = sum(len(r) for r in rows)
            corr = sum(1 for r in rows for _, c in r if c) / n
            print(f"  {var:<8} {len(rows):>6} {n:>4} {sum(consistencies) / len(consistencies):>20.2f} {corr:>8.2f}")


if __name__ == "__main__":
    main()
