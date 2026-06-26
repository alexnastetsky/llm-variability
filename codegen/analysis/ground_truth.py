#!/usr/bin/env python3
"""Gold behavior per case = the reference solution's own behavioral identity.

Run each data/reference/<case>.py through the SAME oracle the candidates use. The
reference passes every named test and matches itself on the corpus, so its
behavioral canonical is the "correct" identity every run is graded against
(analogue of analysis/ground_truth.py in the triage experiment).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import run_tests  # noqa: E402  (tools/run_tests.py)


def gold_behavior():
    """{case_id: evaluate-record of the reference solution}."""
    out = {}
    for cid in run_tests.CASES:
        ref = os.path.join(ROOT, "data", "reference", f"{cid}.py")
        out[cid] = run_tests.evaluate(cid, ref)
    return out


if __name__ == "__main__":
    import json
    g = {cid: rec["behavior"] for cid, rec in gold_behavior().items()}
    print(json.dumps(g, indent=2))
