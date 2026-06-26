# Named test suite for run_length_encode. Each entry is (args_tuple, expected).
TESTS = [
    (("",), ""),
    (("a",), "a"),
    (("abc",), "abc"),
    (("aaaa",), "a4"),
    (("aaabccccd",), "a3bc4d"),
    (("a" * 12,), "a12"),
    (("aaa222",), "a323"),
    (("aabbbc",), "a2b3c"),
    (("xyz",), "xyz"),
    (("wwwwwwwwww",), "w10"),
]
