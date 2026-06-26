#!/usr/bin/env python3
"""Output-variability metrics across the three experiment conditions.

For each condition x case, over the K repeated runs, computes:
  - consistency rate   : share of runs equal to the modal output (1.0 = identical every time)
  - distinct outputs   : number of unique outputs seen
  - normalized entropy : Shannon entropy of the output distribution / log(K)  (0 = identical)
  - correctness rate   : share matching deterministic ground truth
  - failure signatures : why wrong outputs were wrong (esp. dropped long-range hand-offs)

"Output" = the tuple of gradeable fields (summary excluded; it is free text).
Missing/invalid runs collapse to a single "INVALID" bucket (a distinct, wrong output).

Usage: python3 analysis/metrics.py [--results-root results]
"""
import argparse
import json
import math
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
import sys  # noqa: E402
sys.path.insert(0, ROOT)
from analysis.ground_truth import ground_truth, GRADEABLE_FIELDS  # noqa: E402

CONDITIONS = [
    ("Option 1 (Claude Code orchestrates)", "option1_default"),
    ("Option 2 (code orchestrates)", "option2"),
]


def canonical(obj):
    """Hashable identity of a result's gradeable fields, or None if unusable."""
    if not isinstance(obj, dict) or "_error" in obj:
        return None
    try:
        parts = []
        for f in GRADEABLE_FIELDS:
            v = obj[f]
            if isinstance(v, float):
                v = round(v, 2)
            if f == "category" and isinstance(v, str):
                v = v.strip().lower()
            parts.append((f, v))
        return tuple(parts)
    except KeyError:
        return None


def truth_canonical(cid, truth):
    return tuple((f, round(truth[cid][f], 2) if isinstance(truth[cid][f], float) else truth[cid][f])
                 for f in GRADEABLE_FIELDS)


def failure_signature(obj, cid, truth):
    """Classify why a run is wrong. Returns a list of signature tags."""
    if not isinstance(obj, dict) or "_error" in obj:
        return ["invalid_or_error"]
    can = canonical(obj)
    if can is None:
        return ["invalid_or_error"]
    t = truth[cid]
    tags = []
    for f in ["account_id", "tier", "unit_price", "quantity", "subtotal",
              "volume_discount_pct", "tier_discount_pct", "total", "sla_hours",
              "category", "decision"]:
        ov = obj.get(f)
        tv = t[f]
        if isinstance(tv, float) and isinstance(ov, (int, float)):
            if round(ov, 2) != round(tv, 2):
                tags.append(f"wrong_{f}")
        elif (ov.strip().lower() if (f == "category" and isinstance(ov, str)) else ov) != tv:
            tags.append(f"wrong_{f}")
    # dropped long-range hand-off: decision inconsistent with the row's OWN tier+total
    try:
        own_rule = "ESCALATE" if (obj["tier"] == "Enterprise" and obj["total"] > 10000) else "STANDARD"
        if obj["decision"] != own_rule:
            tags.append("decision_inconsistent_with_own_fields")
    except (KeyError, TypeError):
        pass
    return tags or ["wrong_other"]


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


def analyze_condition(cond_dir, truth):
    cases = sorted(truth.keys())
    per_case = {}
    for cid in cases:
        runs = load_runs(os.path.join(cond_dir, cid))
        if not runs:
            continue
        n = len(runs)
        keys = [canonical(r) or ("INVALID",) for r in runs]
        counts = Counter(keys)
        consistency = max(counts.values()) / n
        distinct = len(counts)
        entropy = abs(-sum((c / n) * math.log(c / n) for c in counts.values()))
        norm_entropy = entropy / math.log(n) if n > 1 else 0.0
        tcan = truth_canonical(cid, truth)
        correct = sum(1 for k in keys if k == tcan) / n
        sigs = Counter()
        for r, k in zip(runs, keys):
            if k != tcan:
                sigs.update(failure_signature(r, cid, truth))
        per_case[cid] = dict(n=n, consistency=consistency, distinct=distinct,
                             norm_entropy=norm_entropy, correctness=correct, sigs=sigs)
    return per_case


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", default=os.path.join(ROOT, "results"))
    args = ap.parse_args()
    truth = ground_truth()

    summary = []
    for label, sub in CONDITIONS:
        cond_dir = os.path.join(args.results_root, sub)
        pc = analyze_condition(cond_dir, truth)
        if not pc:
            print(f"\n### {label}\n  (no results found in {cond_dir} — skipped)")
            continue
        agg_sigs = Counter()
        for d in pc.values():
            agg_sigs.update(d["sigs"])
        row = dict(
            label=label,
            consistency=mean([d["consistency"] for d in pc.values()]),
            norm_entropy=mean([d["norm_entropy"] for d in pc.values()]),
            correctness=mean([d["correctness"] for d in pc.values()]),
            cases=len(pc),
            sigs=agg_sigs,
        )
        summary.append(row)
        print(f"\n### {label}   ({row['cases']} cases)")
        print(f"  {'case':<8} {'N':>3} {'consist':>8} {'distinct':>9} {'norm_H':>7} {'correct':>8}")
        for cid in sorted(pc):
            d = pc[cid]
            print(f"  {cid:<8} {d['n']:>3} {d['consistency']:>8.2f} {d['distinct']:>9} "
                  f"{d['norm_entropy']:>7.2f} {d['correctness']:>8.2f}")
        if agg_sigs:
            print("  failure signatures:", dict(agg_sigs.most_common()))

    if len(summary) >= 2:
        print("\n" + "=" * 64)
        print("COMPARISON (averaged over cases) — lower consistency / higher norm_H = MORE variability")
        print("=" * 64)
        print(f"  {'condition':<30} {'consist':>8} {'norm_H':>8} {'correct':>8}")
        for r in summary:
            print(f"  {r['label']:<30} {r['consistency']:>8.2f} {r['norm_entropy']:>8.2f} {r['correctness']:>8.2f}")
        print("\nHypothesis check: expect Option 1 consistency < Option 2 consistency")
        print("(and Option 1 more hand-off failure signatures). Both run on the same")
        print("model at fixed sampling, so the gap reflects orchestration, not temperature.")


if __name__ == "__main__":
    main()
