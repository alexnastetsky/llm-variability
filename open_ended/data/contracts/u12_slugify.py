"""Contract for slugify: the result is lowercase, contains no whitespace, and its
alphanumeric content matches the input's (lowercased). The word SEPARATOR and how
punctuation is handled are the divergence axes."""


def _alnum(s):
    return "".join(c for c in s.lower() if c.isalnum())


def check(args, output):
    s = args[0]
    if not isinstance(output, str):
        return False
    if any(c.isspace() for c in output):
        return False
    if output != output.lower():
        return False
    return _alnum(output) == _alnum(s)
