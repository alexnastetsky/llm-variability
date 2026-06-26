#!/usr/bin/env python3
"""Generate per-task prompt VARIANTS from authored rule sources + verified tests.

For each case, emits data/specs/<case>/v1.md .. vN.md (N = cases.json[case].n_variants).
Every variant shares the SAME authored rules (data/specs_src/<case>.md) and differs only in
(a) a small intro wording and (b) which worked examples it shows — examples are drawn from the
VERIFIED named tests (data/tests/<case>.py), so they cannot drift from the reference behavior.
This gives "different inputs for the same task" with zero risk of changing the correct answer.

Run: python3 tools/build_specs.py
"""
import importlib.util
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")

INTROS = [
    "Implement the following function.",
    "Your task: write the function described below to this specification.",
    "Define the function specified here so that it meets every rule.",
]


def load_tests(cid):
    spec = importlib.util.spec_from_file_location("t_" + cid, os.path.join(DATA, "tests", f"{cid}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.TESTS


def example_line(func, args, expected):
    call = f"{func}({', '.join(repr(a) for a in args)})"
    if isinstance(expected, dict) and "__raises__" in expected:
        return f"- `{call}` raises `{expected['__raises__']}`"
    return f"- `{call}` → `{expected!r}`"


def main():
    cases = json.load(open(os.path.join(DATA, "cases.json")))
    for cid, meta in cases.items():
        func = meta["func_name"]
        n_var = meta.get("n_variants", 3)
        rules = open(os.path.join(DATA, "specs_src", f"{cid}.md")).read().rstrip()
        tests = load_tests(cid)
        out_dir = os.path.join(DATA, "specs", cid)
        # clean any prior flat file and stale dir
        flat = os.path.join(DATA, "specs", f"{cid}.md")
        if os.path.exists(flat):
            os.remove(flat)
        if os.path.isdir(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir)
        for i in range(n_var):
            picks = [t for j, t in enumerate(tests) if j % n_var == i] or tests[:4]
            examples = "\n".join(example_line(func, args, exp) for args, exp in picks)
            body = f"{INTROS[i % len(INTROS)]}\n\n{rules}\n\n## Examples\n\n{examples}\n"
            with open(os.path.join(out_dir, f"v{i + 1}.md"), "w") as fh:
                fh.write(body)
        print(f"{cid}: wrote {n_var} variants ({func})")


if __name__ == "__main__":
    main()
