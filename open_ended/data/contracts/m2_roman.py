"""Contract for to_roman: WELL-SPECIFIED control — there is exactly one correct
Roman numeral per integer, so every valid run must produce it. Used to confirm that
multi-file structure alone does not induce behavioral divergence."""

_TABLE = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
          (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def _correct(n):
    out = []
    for v, sym in _TABLE:
        while n >= v:
            out.append(sym)
            n -= v
    return "".join(out)


def check(args, output):
    return output == _correct(args[0])
