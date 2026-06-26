# run_length_encode

Implement:

```python
def run_length_encode(s: str) -> str
```

Encode the string by collapsing **runs** of identical consecutive characters.

- A run of length `n > 1` is emitted as the character followed by the decimal count: `"aaaa"` → `"a4"`.
- A run of length **exactly 1** is emitted as the **bare character**, with **no** `1`: `"abc"` → `"abc"`.
- Counts are decimal with no leading zeros. Process the string left to right; preserve order.
- The empty string encodes to the empty string.
- Note: characters may themselves be digits; still encode by repetition count, e.g. `"aaa222"` → `"a3"` + `"23"` = `"a323"`.

Examples:
- `run_length_encode("")` → `""`
- `run_length_encode("abc")` → `"abc"`
- `run_length_encode("aaaa")` → `"a4"`
- `run_length_encode("aaabccccd")` → `"a3bc4d"`
- `run_length_encode("a" * 12)` → `"a12"`
- `run_length_encode("aaa222")` → `"a323"`
