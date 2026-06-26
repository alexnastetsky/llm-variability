#!/usr/bin/env python3
"""Output-variability metrics for the codegen experiment, at three altitudes.

For each condition x case, over the K repeated runs, computes — separately for the
TEXT, STRUCTURAL, and BEHAVIORAL identity of each run:
  - consistency rate   : share of runs equal to the modal output (1.0 = identical every time)
  - distinct outputs   : number of unique identities seen
  - normalized entropy : Shannon entropy / log(K)  (0 = identical)
and once, against the reference's behavior:
  - correctness rate   : share whose behavior is correct (all named tests pass AND matches reference on the corpus)
  - failure signatures : why wrong runs were wrong (incl. wrong_on_corpus — divergence the named tests missed)

The BEHAVIORAL altitude is the primary metric and the analogue of the triage
experiment's gradeable-field tuple: it is invariant to source text, so it measures
variability in what the code *does*, not how it is written.

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
from analysis.ground_truth import gold_behavior  # noqa: E402

CONDITIONS = [
    ("Option 1 (Claude Code orchestrates)", "option1_default"),
    ("Option 2 (code orchestrates)", "option2"),
]
ALTITUDES = ["text", "struct", "behav"]


def canonical(obj, altitude):
    """Hashable identity of a run at a given altitude, or None if unusable."""
    if not isinstance(obj, dict) or "_error" in obj:
        return None
    try:
        if altitude == "text":
            return ("text", obj["source_sha256"])
        if altitude == "struct":
            return ("struct", obj["structural_sha256"])
        b = obj["behavior"]
        return ("behav", b["status"], tuple(b["test_results"]), b["corpus_vector_sha256"])
    except KeyError:
        return None


def truth_behav(cid, gold):
    return canonical(gold[cid], "behav")


def failure_signature(obj, cid, gold):
    """Classify why a run's behavior is wrong. Returns a list of signature tags."""
    if not isinstance(obj, dict) or "_error" in obj:
        return ["invalid_or_error"]
    b = obj.get("behavior")
    if not isinstance(b, dict):
        return ["invalid_or_error"]
    status = b.get("status")
    if status == "blocked":
        return ["blocked_unsafe"]
    if status == "compile_error":
        return ["compile_error"]
    if status == "timeout":
        return ["timeout"]
    if status == "runtime_error_global":
        return ["runtime_exception"]
    tags = []
    tr = b.get("test_results", [])
    n_pass = sum(1 for x in tr if x)
    if 0 < n_pass < len(tr):
        tags.append("partial_pass")
    for i, ok in enumerate(tr):
        if not ok:
            tags.append(f"wrong_on_test_t{i}")
    # behavioral divergence found ONLY by the differential corpus (named tests passed)
    if n_pass == len(tr) and not b.get("matches_reference", False):
        tags.append("wrong_on_corpus")
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


def _consistency(keys):
    n = len(keys)
    counts = Counter(keys)
    consistency = max(counts.values()) / n
    distinct = len(counts)
    entropy = abs(-sum((c / n) * math.log(c / n) for c in counts.values()))
    norm_entropy = entropy / math.log(n) if n > 1 else 0.0
    return consistency, distinct, norm_entropy


def analyze_condition(cond_dir, gold):
    cases = sorted(gold.keys())
    per_case = {}
    for cid in cases:
        runs = load_runs(os.path.join(cond_dir, cid))
        if not runs:
            continue
        n = len(runs)
        alt = {}
        for a in ALTITUDES:
            keys = [canonical(r, a) or ("INVALID",) for r in runs]
            alt[a] = _consistency(keys)
        tcan = truth_behav(cid, gold)
        behav_keys = [canonical(r, "behav") or ("INVALID",) for r in runs]
        correct = sum(1 for k in behav_keys if k == tcan) / n
        sigs = Counter()
        for r, k in zip(runs, behav_keys):
            if k != tcan:
                sigs.update(failure_signature(r, cid, gold))
        per_case[cid] = dict(n=n, alt=alt, correctness=correct, sigs=sigs)
    return per_case


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", default=os.path.join(ROOT, "results"))
    args = ap.parse_args()
    gold = gold_behavior()

    summary = []
    for label, sub in CONDITIONS:
        cond_dir = os.path.join(args.results_root, sub)
        pc = analyze_condition(cond_dir, gold)
        if not pc:
            print(f"\n### {label}\n  (no results found in {cond_dir} — skipped)")
            continue
        agg_sigs = Counter()
        for d in pc.values():
            agg_sigs.update(d["sigs"])
        row = dict(
            label=label,
            text=mean([d["alt"]["text"][0] for d in pc.values()]),
            struct=mean([d["alt"]["struct"][0] for d in pc.values()]),
            behav=mean([d["alt"]["behav"][0] for d in pc.values()]),
            behav_H=mean([d["alt"]["behav"][2] for d in pc.values()]),
            correctness=mean([d["correctness"] for d in pc.values()]),
            cases=len(pc),
            sigs=agg_sigs,
        )
        summary.append(row)
        print(f"\n### {label}   ({row['cases']} cases)")
        print(f"  consistency by altitude (1.00 = identical every run):")
        print(f"  {'case':<8} {'N':>3} {'text':>6} {'struct':>7} {'behav':>6} {'behav_H':>8} {'correct':>8}")
        for cid in sorted(pc):
            d = pc[cid]
            print(f"  {cid:<8} {d['n']:>3} {d['alt']['text'][0]:>6.2f} {d['alt']['struct'][0]:>7.2f} "
                  f"{d['alt']['behav'][0]:>6.2f} {d['alt']['behav'][2]:>8.2f} {d['correctness']:>8.2f}")
        if agg_sigs:
            print("  failure signatures:", dict(agg_sigs.most_common()))

    if len(summary) >= 2:
        print("\n" + "=" * 70)
        print("COMPARISON (mean over cases) — lower behav consistency = MORE behavioral variability")
        print("=" * 70)
        print(f"  {'condition':<30} {'text':>6} {'struct':>7} {'behav':>6} {'correct':>8}")
        for r in summary:
            print(f"  {r['label']:<30} {r['text']:>6.2f} {r['struct']:>7.2f} {r['behav']:>6.2f} {r['correctness']:>8.2f}")
        print("\nExpect text << struct <= behav (source varies; behavior is the stable unit).")
        print("Hypothesis check: is Option 1 behavioral consistency < Option 2's? Both run the")
        print("same model at fixed sampling, so any gap reflects orchestration, not temperature.")


if __name__ == "__main__":
    main()
