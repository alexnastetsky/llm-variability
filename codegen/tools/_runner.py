#!/usr/bin/env python3
"""Subprocess runner: load a candidate solution and evaluate it on a list of inputs.

Invoked (never imported) by tools/run_tests.py in an isolated, resource-limited
child process. Reads a JSON job from argv, imports the candidate module by path,
calls the target function on each input, and prints a JSON result vector to stdout.

Contract:
  argv: <solution_path> <func_name> <inputs_json_path>
  inputs_json: {"inputs": [[arg0, arg1, ...], ...]}   # each element is an args list
  stdout:      {"results": [ {"v": <canonical-json-string>} | {"e": "<ExcType>"} , ... ]}

Each result is canonicalized to a stable string so behavioral comparison across
runs is exact and type-stable. An exception is recorded by its type name only.
"""
import importlib.util
import json
import sys


def canon(value):
    """Stable string identity of a return value, JSON when possible else repr."""
    try:
        return json.dumps(value, sort_keys=True, default=repr)
    except (TypeError, ValueError):
        return repr(value)


def main():
    solution_path, func_name, inputs_path = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(inputs_path) as fh:
        inputs = json.load(fh)["inputs"]

    spec = importlib.util.spec_from_file_location("candidate", solution_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # import-time errors propagate -> nonzero exit
    func = getattr(module, func_name)

    results = []
    for args in inputs:
        try:
            results.append({"v": canon(func(*args))})
        except Exception as exc:  # noqa: BLE001 — exception TYPE is part of behavior
            results.append({"e": type(exc).__name__})
    sys.stdout.write(json.dumps({"results": results}))


if __name__ == "__main__":
    main()
