#!/usr/bin/env python3
"""Seeded corpus generators for the open-ended tasks. Inputs are biased toward the
regions where underspecified tasks admit multiple valid behaviors (score ties,
exact halves, duplicate values, even-length lists) so divergence — if it exists —
has every chance to appear. Fixed seeds make every run's inputs identical and thus
behaviorally comparable across runs.
"""
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
with open(os.path.join(ROOT, "data", "cases.json")) as _f:
    CASES = json.load(_f)


def _gen_u1(rng, n):  # rank_items: unique names, small score range -> many ties
    out = []
    for _ in range(n):
        m = rng.randint(1, 8)
        items = [[f"n{i}", rng.randint(0, 3)] for i in range(m)]
        rng.shuffle(items)
        out.append([items])
    return out


def _gen_u2(rng, n):  # round_all: lots of exact halves and quarter points
    out = []
    for _ in range(n):
        m = rng.randint(1, 8)
        nums = [rng.randint(-10, 10) + rng.choice([0.0, 0.5, 0.5, 0.25, 0.75]) for _ in range(m)]
        out.append([nums])
    return out


def _gen_u3(rng, n):  # top_k: duplicate values + k spanning edge values
    out = []
    for _ in range(n):
        m = rng.randint(1, 9)
        nums = [rng.randint(0, 5) for _ in range(m)]
        k = rng.randint(0, m + 1)
        out.append([nums, k])
    return out


def _gen_u10(rng, n):  # summary: even & odd lengths to exercise median convention
    out = []
    for _ in range(n):
        m = rng.randint(1, 9)
        out.append([[rng.randint(0, 20) for _ in range(m)]])
    return out


def _gen_ctl1(rng, n):  # to_roman: valid integers 1..3999
    return [[rng.randint(1, 3999)] for _ in range(n)]


def _gen_u4(rng, n):  # dedup: many duplicates over a small domain
    return [[[rng.randint(0, 4) for _ in range(rng.randint(0, 10))]] for _ in range(n)]


def _gen_u5(rng, n):  # argmax: small value range -> frequent tied maxima
    out = []
    for _ in range(n):
        m = rng.randint(1, 8)
        out.append([[rng.randint(0, 3) for _ in range(m)]])
    return out


def _gen_u6(rng, n):  # median_of: even & odd lengths
    out = []
    for _ in range(n):
        m = rng.randint(1, 9)
        out.append([[rng.randint(0, 20) for _ in range(m)]])
    return out


def _gen_u7(rng, n):  # most_common: small domain -> frequent tied modes
    out = []
    for _ in range(n):
        m = rng.randint(1, 10)
        out.append([[rng.randint(0, 3) for _ in range(m)]])
    return out


def _gen_u8(rng, n):  # top_k_indices: duplicate values + k spanning edges
    out = []
    for _ in range(n):
        m = rng.randint(1, 9)
        nums = [rng.randint(0, 5) for _ in range(m)]
        out.append([nums, rng.randint(0, m + 1)])
    return out


def _gen_u9(rng, n):  # parse_bool: canonical, cased, and ambiguous strings
    vocab = ["true", "false", "True", "FALSE", " true ", "false ",
             "yes", "no", "1", "0", "on", "off", "y", "n", "", "TRUE", "t", "f"]
    return [[rng.choice(vocab)] for _ in range(n)]


_WORDS = ["the", "a", "an", "of", "in", "on", "and", "or", "to", "for",
          "quick", "brown", "fox", "data", "model", "report", "alpha", "beta", "city", "river"]


def _gen_u11(rng, n):  # titlecase: phrases with small words (article-capitalization axis)
    return [[" ".join(rng.choice(_WORDS) for _ in range(rng.randint(2, 6)))] for _ in range(n)]


def _gen_u12(rng, n):  # slugify: mixed case + punctuation + spacing (separator axis)
    seps = [" ", "  ", ", ", " - ", "! ", ": "]
    out = []
    for _ in range(n):
        words = [rng.choice(_WORDS) for _ in range(rng.randint(2, 5))]
        words = [w.capitalize() if rng.random() < 0.4 else w for w in words]
        s = rng.choice(seps).join(words) + rng.choice(["", "!", ".", ""])
        out.append([s])
    return out


def _gen_u13(rng, n):  # initials: multi-word capitalized names (formatting axis)
    parts = ["john", "ronald", "reuel", "tolkien", "mary", "jane", "li", "anna", "bob", "smith", "van", "de"]
    out = []
    for _ in range(n):
        name = " ".join(rng.choice(parts).capitalize() for _ in range(rng.randint(2, 4)))
        out.append([name])
    return out


def _gen_u14(rng, n):  # camel_to_snake: camelCase ids incl acronym runs (split-boundary axis)
    frags = ["get", "set", "parse", "value", "name", "data", "file", "handler", "response", "request", "node"]
    acrs = ["HTTP", "XML", "ID", "URL", "API", "JSON"]
    out = []
    for _ in range(n):
        s = rng.choice(frags)
        for _ in range(rng.randint(1, 3)):
            if rng.random() < 0.35:
                s += rng.choice(acrs)
            else:
                s += rng.choice(frags).capitalize()
        out.append([s])
    return out


def _gen_u15(rng, n):  # normalize_whitespace: leading/trailing/mixed whitespace (trim+collapse axis)
    ws = [" ", "  ", "   ", "\t", "\n", " \t "]
    out = []
    for _ in range(n):
        words = [rng.choice(_WORDS) for _ in range(rng.randint(1, 5))]
        s = rng.choice(ws).join(words)
        if rng.random() < 0.5:
            s = rng.choice(ws) + s
        if rng.random() < 0.5:
            s = s + rng.choice(ws)
        out.append([s])
    return out


def _gen_u16(rng, n):  # strip_punctuation: apostrophes/hyphens + core punct (which-to-remove axis)
    toks = ["don't", "it's", "well-being", "hello", "world", "state-of-the-art", "yes", "no", "data"]
    puncts = [", ", ". ", "! ", "? ", "; ", " "]
    out = []
    for _ in range(n):
        words = [rng.choice(toks) for _ in range(rng.randint(2, 5))]
        s = "".join(w + rng.choice(puncts) for w in words).strip()
        out.append([s])
    return out


def _gen_ctl2(rng, n):  # reverse_string: arbitrary ascii (fully specified control)
    alpha = "abcDEF123 .,!-"
    return [["".join(rng.choice(alpha) for _ in range(rng.randint(0, 12)))] for _ in range(n)]


_GENERATORS = {
    "u1_rank_items": _gen_u1,
    "u2_round_all": _gen_u2,
    "u3_top_k": _gen_u3,
    "u4_dedup": _gen_u4,
    "u5_argmax": _gen_u5,
    "u6_median": _gen_u6,
    "u7_most_common": _gen_u7,
    "u8_top_k_indices": _gen_u8,
    "u9_parse_bool": _gen_u9,
    "u10_stats": _gen_u10,
    "u11_titlecase": _gen_u11,
    "u12_slugify": _gen_u12,
    "u13_initials": _gen_u13,
    "u14_camel_to_snake": _gen_u14,
    "u15_normalize_whitespace": _gen_u15,
    "u16_strip_punctuation": _gen_u16,
    "ctl1_roman": _gen_ctl1,
    "ctl2_reverse": _gen_ctl2,
}


def corpus_inputs(case_id):
    meta = CASES[case_id]
    rng = random.Random(meta["corpus_seed"])
    return _GENERATORS[case_id](rng, meta["n_corpus"])


if __name__ == "__main__":
    import sys
    cid = sys.argv[1] if len(sys.argv) > 1 else "u1_rank_items"
    print(f"{cid}: {len(corpus_inputs(cid))} inputs; first 3 = {corpus_inputs(cid)[:3]}")
