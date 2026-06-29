"""Contract for initials: the letters of the result (uppercased) must be exactly the
first letter of each whitespace-separated token of the name. HOW they are formatted
(periods, spacing, case in the output string) is the divergence axis."""


def check(args, output):
    name = args[0]
    if not isinstance(output, str):
        return False
    want = "".join(tok[0] for tok in name.split() if tok).upper()
    got = "".join(c for c in output if c.isalpha()).upper()
    return got == want
