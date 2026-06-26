# Named test suite for balanced_parens. Each entry is (args_tuple, expected).
TESTS = [
    (("",), True),
    (("()",), True),
    (("()[]{}",), True),
    (("{[()]}",), True),
    (("a(b[c]d)e",), True),
    (("(",), False),
    ((")",), False),
    ((")(",), False),
    (("([)]",), False),
    (("(]",), False),
    (("{[}]",), False),
    (("((()))",), True),
    (("no brackets here",), True),
]
