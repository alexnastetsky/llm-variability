"""Contract for normalize_whitespace: the result has the same words in the same order
as the input (whitespace-separated). Whether leading/trailing whitespace is trimmed and
which internal whitespace runs are collapsed (and to what) is the divergence axis."""


def check(args, output):
    s = args[0]
    if not isinstance(output, str):
        return False
    return output.split() == s.split()
