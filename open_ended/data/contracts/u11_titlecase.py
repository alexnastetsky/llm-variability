"""Contract for titlecase: the result is the input with only letter-case changed, and
the first alphabetic character is uppercase. WHICH words get capitalized (e.g. whether
small words like 'the'/'of' are lowercased) is the divergence axis."""


def check(args, output):
    s = args[0]
    if not isinstance(output, str):
        return False
    if output.lower() != s.lower():  # only casing may differ
        return False
    for ch in output:
        if ch.isalpha():
            return ch.isupper()  # first alphabetic char must be capitalized
    return True  # no letters -> vacuously fine
