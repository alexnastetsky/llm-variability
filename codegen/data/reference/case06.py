import re

_TOKEN = re.compile(r"\d+|[-+*/%()]")


def _trunc_div(a, b):
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def eval_expr(expr: str) -> int:
    tokens = []
    i, n = 0, len(expr)
    while i < n:
        if expr[i].isspace():
            i += 1
            continue
        m = _TOKEN.match(expr, i)
        if not m:
            raise ValueError(f"bad character at {i}")
        tokens.append(m.group(0))
        i = m.end()
    if not tokens:
        raise ValueError("empty expression")

    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def advance():
        nonlocal pos
        t = tokens[pos]
        pos += 1
        return t

    def parse_expr():
        val = parse_term()
        while peek() in ("+", "-"):
            op = advance()
            rhs = parse_term()
            val = val + rhs if op == "+" else val - rhs
        return val

    def parse_term():
        val = parse_factor()
        while peek() in ("*", "/", "%"):
            op = advance()
            rhs = parse_factor()
            if op == "*":
                val = val * rhs
            elif op == "/":
                if rhs == 0:
                    raise ZeroDivisionError("division by zero")
                val = _trunc_div(val, rhs)
            else:
                if rhs == 0:
                    raise ZeroDivisionError("modulo by zero")
                val = val - rhs * _trunc_div(val, rhs)
        return val

    def parse_factor():
        t = peek()
        if t is None:
            raise ValueError("unexpected end of input")
        if t == "+":
            advance()
            return parse_factor()
        if t == "-":
            advance()
            return -parse_factor()
        if t == "(":
            advance()
            val = parse_expr()
            if peek() != ")":
                raise ValueError("missing closing paren")
            advance()
            return val
        if t.isdigit():
            advance()
            return int(t)
        raise ValueError(f"unexpected token {t!r}")

    result = parse_expr()
    if pos != len(tokens):
        raise ValueError("trailing input")
    return result
