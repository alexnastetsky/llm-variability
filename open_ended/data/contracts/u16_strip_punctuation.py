"""Contract for strip_punctuation: all letters/digits/whitespace of the input are
preserved in order, and at least the core punctuation `.,!?;:` is removed. WHICH other
punctuation is removed (notably apostrophes and hyphens) is the divergence axis."""

CORE = set(".,!?;:")


def _keep(s):
    return [c for c in s if c.isalnum() or c.isspace()]


def check(args, output):
    s = args[0]
    if not isinstance(output, str):
        return False
    if _keep(output) != _keep(s):  # alnum + whitespace fully preserved, in order
        return False
    return not any(c in CORE for c in output)  # core punctuation must be gone
