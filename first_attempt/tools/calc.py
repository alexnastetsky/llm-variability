#!/usr/bin/env python3
"""Deterministic arithmetic tool. Safe (ast-based) evaluation of +-*/() and numbers.

CLI:    python3 tools/calc.py "15 * 999.99"
Import: from tools.calc import calc; calc("15 * 999.99")
"""
import ast
import operator
import sys

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"non-numeric constant: {node.value!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError(f"unsupported expression element: {ast.dump(node)}")


def calc(expr: str):
    """Evaluate an arithmetic expression and return a number."""
    return _eval(ast.parse(expr, mode="eval"))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: calc.py \"<arithmetic expression>\"", file=sys.stderr)
        sys.exit(2)
    print(calc(sys.argv[1]))
