#!/usr/bin/env python3
"""Subprocess runner for a (possibly multi-file) candidate solution.

Adds the solution directory to sys.path, imports the entry module, and calls the
target function on each input. Intra-solution imports use absolute module names
(e.g. `from core import ...`), which resolve because the solution dir is on the path.

  argv:   <solution_dir> <entry_module> <func_name> <inputs_json_path>
  stdout: {"results": [ {"v": <canonical-json>} | {"e": "<ExcType>"} , ... ]}
"""
import importlib
import json
import sys


def canon(value):
    try:
        return json.dumps(value, sort_keys=True, default=repr)
    except (TypeError, ValueError):
        return repr(value)


def main():
    sol_dir, entry, func_name, inputs_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    with open(inputs_path) as fh:
        inputs = json.load(fh)["inputs"]
    sys.path.insert(0, sol_dir)
    module = importlib.import_module(entry)  # import-time errors propagate -> nonzero exit
    func = getattr(module, func_name)
    results = []
    for args in inputs:
        try:
            results.append({"v": canon(func(*args))})
        except Exception as exc:  # noqa: BLE001
            results.append({"e": type(exc).__name__})
    sys.stdout.write(json.dumps({"results": results}))


if __name__ == "__main__":
    main()
