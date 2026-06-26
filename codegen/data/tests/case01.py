# Named test suite for roman_to_int. Each entry is (args_tuple, expected).
TESTS = [
    (("I",), 1),
    (("III",), 3),
    (("IV",), 4),
    (("IX",), 9),
    (("LVIII",), 58),
    (("XL",), 40),
    (("XC",), 90),
    (("CD",), 400),
    (("CM",), 900),
    (("MCMXCIV",), 1994),
    (("MMMCMXCIX",), 3999),
    (("MMXXV",), 2025),
]
