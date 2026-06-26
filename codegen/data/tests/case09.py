# Named test suite for wildcard_match. Each entry is (args_tuple, expected).
TESTS = [
    (("a*b", "aXXXb"), True),
    (("a*b", "ab"), True),
    (("?", ""), False),
    (("*", ""), True),
    (("", ""), True),
    (("", "x"), False),
    (("a?c", "abc"), True),
    (("a?c", "ac"), False),
    (("**a*", "ba"), True),
    (("a*b*c", "axbyc"), True),
    (("a*b*c", "axbyd"), False),
    (("*?*", "a"), True),
    (("*?*", ""), False),
]
