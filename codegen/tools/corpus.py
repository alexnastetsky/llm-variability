#!/usr/bin/env python3
"""Seeded differential-testing corpus generators (one per case).

Each generator returns a list of argument tuples (as lists, JSON-friendly). The
seed and size live in data/cases.json, so every run of every option is evaluated
on the IDENTICAL input set -> behavioral output vectors are directly comparable.
Generators are pinned (random.Random(seed)); do not change them without bumping
the seed, or cached reference vectors will silently mismatch.
"""
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
with open(os.path.join(ROOT, "data", "cases.json")) as _f:
    CASES = json.load(_f)


def _int_to_roman(n):
    table = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
             (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
             (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = []
    for value, sym in table:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out)


def _gen_case01(rng, n):
    # valid Roman numerals in 1..3999
    return [[_int_to_roman(rng.randint(1, 3999))] for _ in range(n)]


def _gen_case02(rng, n):
    # random lists of [start, end] intervals (start <= end), incl. empty/overlap/nest
    out = []
    for _ in range(n):
        k = rng.randint(0, 8)
        intervals = []
        for _ in range(k):
            start = rng.randint(-20, 20)
            end = start + rng.randint(0, 10)
            intervals.append([start, end])
        out.append([intervals])
    return out


def _gen_case03(rng, n):
    # strings mixing brackets + filler; biased so some are balanced, some not
    alphabet = list("()[]{}") + list("abc 12")
    out = []
    for _ in range(n):
        length = rng.randint(0, 14)
        out.append(["".join(rng.choice(alphabet) for _ in range(length))])
    return out


def _gen_case04(rng, n):
    # strings over a small alphabet (incl. digits) with frequent runs
    alphabet = list("aab2c")  # repetition bias -> runs; '2' exercises digit ambiguity
    out = []
    for _ in range(n):
        length = rng.randint(0, 16)
        out.append(["".join(rng.choice(alphabet) for _ in range(length))])
    return out


def _gen_case05(rng, n):
    # (n >= 0, base in 2..16)
    return [[rng.randint(0, 1_000_000), rng.randint(2, 16)] for _ in range(n)]


_GENERATORS = {
    "case01": _gen_case01,
    "case02": _gen_case02,
    "case03": _gen_case03,
    "case04": _gen_case04,
    "case05": _gen_case05,
}


def corpus_inputs(case_id):
    """Return the fixed, seeded list of argument lists for a case."""
    meta = CASES[case_id]
    rng = random.Random(meta["corpus_seed"])
    return _GENERATORS[case_id](rng, meta["n_corpus"])


if __name__ == "__main__":
    import sys
    cid = sys.argv[1] if len(sys.argv) > 1 else "case01"
    inputs = corpus_inputs(cid)
    print(f"{cid}: {len(inputs)} corpus inputs; first 3 = {inputs[:3]}")
