# Named test suite for min_coins. expected may be a value or {"__raises__": "ExcType"}.
TESTS = [
    (([1, 2, 5], 11), 3),
    (([2], 3), -1),
    (([1, 3, 4], 6), 2),
    (([5, 2, 1], 0), 0),
    (([], 0), 0),
    (([], 5), -1),
    (([7], 7), 1),
    (([3, 7], 5), -1),
    (([1, 5, 6, 9], 11), 2),
    (([1, 2, 5], 100), 20),
    (([1, 2], -1), {"__raises__": "ValueError"}),
    (([0, 1], 5), {"__raises__": "ValueError"}),
    (([2, 2], 4), {"__raises__": "ValueError"}),
]
