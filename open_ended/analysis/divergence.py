#!/usr/bin/env python3
"""Characterize WHAT diverged, per condition x case.

For each task where the valid runs split into >1 distinct behavioral fingerprint, this
groups the runs, replays one representative per group over the seeded corpus, finds the
first corpus input on which the groups disagree, and prints that input with each group's
output — alongside the task's intended `axis` (from cases.json) and the group sizes.

This is what populates the "diverging axis + split" column of the report.

Usage: python3 analysis/divergence.py [--results-root results]
"""
import argparse
import collections
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import run_tests  # noqa: E402
import corpus  # noqa: E402

CASES = run_tests.CASES
CONDITIONS = [("Option 1 (Claude Code orchestrates)", "option1_default"),
              ("Option 2 (code orchestrates)", "option2")]


def _replay(case_id, files):
    meta = CASES[case_id]
    with tempfile.TemporaryDirectory(prefix="div-") as d:
        for name, body in files.items():
            with open(os.path.join(d, os.path.basename(name)), "w") as fh:
                fh.write(body)
        status, results = run_tests._run_inputs(
            d, meta["entry"], meta["func_name"], corpus.corpus_inputs(case_id), meta.get("timeout_s", 5.0))
    return results


def _fmt(res):
    return res["v"] if "v" in res else f"raises {res.get('e')}"


def analyze(results_root):
    inputs_by_case = {cid: corpus.corpus_inputs(cid) for cid in CASES}
    for label, sub in CONDITIONS:
        print(f"\n### {label}")
        for cid in CASES:
            cdir = os.path.join(results_root, sub, cid)
            if not os.path.isdir(cdir):
                continue
            groups = collections.defaultdict(list)
            for fn in sorted(os.listdir(cdir)):
                if not fn.endswith(".json"):
                    continue
                d = json.load(open(os.path.join(cdir, fn)))
                if isinstance(d, dict) and "_error" not in d and d.get("valid"):
                    groups[d["behavior_fingerprint"]].append(d)
            axis = CASES[cid]["axis"]
            tag = " [CONTROL]" if CASES[cid].get("control") else ""
            if len(groups) <= 1:
                print(f"  {cid:<22}{tag} 1 behavior  (axis: {axis})")
                continue
            sizes = sorted((len(v) for v in groups.values()), reverse=True)
            print(f"  {cid:<22}{tag} {len(groups)} behaviors, split {sizes}  (axis: {axis})")
            # replay representatives and find a distinguishing input
            reps = [v[0] for v in groups.values()]
            vecs = [_replay(cid, r["files"]) for r in reps]
            inputs = inputs_by_case[cid]
            for j in range(min(len(inputs), *(len(v) for v in vecs))):
                outs = [v[j] for v in vecs]
                if len({json.dumps(o, sort_keys=True) for o in outs}) > 1:
                    print(f"      e.g. input {inputs[j]}:")
                    for grp, v in zip(groups.values(), vecs):
                        print(f"        ({len(grp):>2} runs) -> {_fmt(v[j])}")
                    break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", default=os.path.join(ROOT, "results"))
    analyze(ap.parse_args().results_root)


if __name__ == "__main__":
    main()
