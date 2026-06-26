# int_to_base

Implement:

```python
def int_to_base(n: int, base: int) -> str
```

Convert a non-negative integer `n` to its string representation in the given `base`.

- `base` is always an integer in **2..16** (inclusive); `n` is always `>= 0`.
- Digits use the lowercase alphabet `0-9a-f` (so digit 10 is `"a"`, …, digit 15 is `"f"`).
- There are **no** leading zeros, except that `int_to_base(0, base)` returns `"0"`.
- Return the representation as a `str`.

Examples:
- `int_to_base(0, 2)` → `"0"`
- `int_to_base(5, 2)` → `"101"`
- `int_to_base(8, 2)` → `"1000"`
- `int_to_base(255, 16)` → `"ff"`
- `int_to_base(123, 10)` → `"123"`
- `int_to_base(31, 16)` → `"1f"`
