# int_to_base

Convert a non-negative integer `n` to its string representation in the given `base`.

- `base` is always an integer in **2..16** (inclusive); `n` is always `>= 0`.
- Digits use the lowercase alphabet `0-9a-f` (so digit 10 is `"a"`, …, digit 15 is `"f"`).
- There are **no** leading zeros, except that `int_to_base(0, base)` returns `"0"`.
- Return the representation as a `str`.
