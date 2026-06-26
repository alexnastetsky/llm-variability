# Named test suite for eval_expr. expected may be a value or {"__raises__": "ExcType"}.
TESTS = [
    (("1+2*3",), 7),
    (("(1+2)*3",), 9),
    (("--3",), 3),
    (("-+-2",), 2),
    (("2*-3",), -6),
    (("7/2",), 3),
    (("-7/2",), -3),
    (("-7%2",), -1),
    (("7%-2",), 1),
    (("  12 - 3 * 4 ",), 0),
    (("10/0",), {"__raises__": "ZeroDivisionError"}),
    (("",), {"__raises__": "ValueError"}),
    (("1 2",), {"__raises__": "ValueError"}),
    (("(1+2",), {"__raises__": "ValueError"}),
    (("2**3",), {"__raises__": "ValueError"}),
]
