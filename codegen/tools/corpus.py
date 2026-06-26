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


def _build_expr(rng, depth):
    """Grammatically valid arithmetic expression string (for case06)."""
    r = rng.random()
    if depth <= 0 or r < 0.4:
        lit = str(rng.randint(0, 99))
        if rng.random() < 0.3:
            lit = rng.choice(["-", "+", "--", "-+"]) + lit
        return lit
    if r < 0.55:
        return "(" + _build_expr(rng, depth - 1) + ")"
    if r < 0.7:
        return rng.choice(["-", "+"]) + _build_expr(rng, depth - 1)
    op = rng.choice(["+", "-", "*", "/", "%"])
    left = _build_expr(rng, depth - 1)
    right = _build_expr(rng, depth - 1)
    if op in ("/", "%") and rng.random() < 0.3:
        right = rng.choice(["0", "(2-2)", "(3-3)"])  # exercise div/mod by zero
    ws = " " * rng.randint(0, 2)
    return left + ws + op + ws + right


def _gen_case06(rng, n):
    malformed = ["1 2", "(1+2", "1)", "1++", "*3", "", "2**3", "1 + ", "a+1", "()", "(1+2))"]
    out = []
    for _ in range(n):
        if rng.random() < 0.15:
            out.append([rng.choice(malformed)])
        else:
            out.append([_build_expr(rng, rng.randint(1, 4))])
    return out


def _gen_case07(rng, n):
    traps = [[1, 3, 4], [1, 5, 6, 9], [1, 4, 5], [2, 3, 7], [1, 7, 10]]
    out = []
    for _ in range(n):
        r = rng.random()
        if r < 0.15:  # invalid inputs -> reference raises ValueError
            bad = rng.choice(["neg_amount", "bad_coin", "dup"])
            if bad == "neg_amount":
                out.append([rng.sample(range(1, 13), rng.randint(1, 4)), -rng.randint(1, 20)])
            elif bad == "bad_coin":
                coins = rng.sample(range(1, 13), rng.randint(1, 4))
                coins[rng.randrange(len(coins))] = rng.choice([0, -2, -1])
                out.append([coins, rng.randint(0, 40)])
            else:
                coins = rng.sample(range(1, 13), rng.randint(2, 4))
                coins.append(coins[0])
                out.append([coins, rng.randint(0, 40)])
        elif r < 0.5:  # greedy-trap shapes
            out.append([list(rng.choice(traps)), rng.randint(0, 60)])
        else:
            out.append([rng.sample(range(1, 13), rng.randint(0, 5)), rng.randint(0, 60)])
    return out


def _gen_case08(rng, n):
    keys = ["a", "b", "c"]
    malformed = [["FOO"], ["SET", "a"], ["SET", "a", True], ["GET"], ["COUNT"],
                 ["SET", "a", "x"], ["BEGIN", "x"], ["SET", "a", False]]
    out = []
    for _ in range(n):
        ops = []
        for _ in range(rng.randint(0, 18)):
            r = rng.random()
            if r < 0.08:
                ops.append([x for x in rng.choice(malformed)])
            elif r < 0.40:
                ops.append(["SET", rng.choice(keys), rng.randint(0, 3)])
            elif r < 0.55:
                ops.append(["GET", rng.choice(keys)])
            elif r < 0.65:
                ops.append(["DELETE", rng.choice(keys)])
            elif r < 0.75:
                ops.append(["COUNT", rng.randint(0, 3)])
            elif r < 0.85:
                ops.append(["BEGIN"])
            elif r < 0.93:
                ops.append(["COMMIT"])
            else:
                ops.append(["ROLLBACK"])
        out.append([ops])
    return out


def _gen_case09(rng, n):
    out = []
    for _ in range(n):
        if rng.random() < 0.5:  # adversarial: derive a pattern from a text
            text = "".join(rng.choice("ab") for _ in range(rng.randint(0, 8)))
            pat, i = [], 0
            while i < len(text):
                rr = rng.random()
                if rr < 0.3:
                    pat.append("*")
                    i += rng.randint(0, 3)
                elif rr < 0.5:
                    pat.append("?")
                    i += 1
                else:
                    pat.append(text[i])
                    i += 1
            if rng.random() < 0.3:
                pat.append("*")
            out.append(["".join(pat), text])
        else:
            pat = "".join(rng.choice("ab*?") for _ in range(rng.randint(0, 8)))
            text = "".join(rng.choice("ab") for _ in range(rng.randint(0, 8)))
            out.append([pat, text])
    return out


def _gen_case10(rng, n):
    out = []
    for _ in range(n):
        nn = rng.randint(0, 8)
        if nn > 0 and rng.random() < 0.1:  # out-of-range endpoint -> ValueError
            out.append([nn, [[rng.randint(0, nn - 1), nn + rng.randint(0, 2)]]])
            continue
        m = rng.randint(0, nn + 3) if nn > 0 else 0
        edges = [[rng.randint(0, nn - 1), rng.randint(0, nn - 1)] for _ in range(m)]
        if edges and rng.random() < 0.2:
            edges.append(list(rng.choice(edges)))  # duplicate edge
        if nn > 0 and rng.random() < 0.1:
            x = rng.randint(0, nn - 1)
            edges.append([x, x])  # self-loop (cycle)
        out.append([nn, edges])
    return out


_GENERATORS = {
    "case01": _gen_case01,
    "case02": _gen_case02,
    "case03": _gen_case03,
    "case04": _gen_case04,
    "case05": _gen_case05,
    "case06": _gen_case06,
    "case07": _gen_case07,
    "case08": _gen_case08,
    "case09": _gen_case09,
    "case10": _gen_case10,
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
