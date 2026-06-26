# merge_intervals

Implement:

```python
def merge_intervals(intervals: list[list[int]]) -> list[list[int]]
```

Given a list of `[start, end]` integer intervals (with `start <= end`), return the minimal list of
merged, non-overlapping intervals, **sorted ascending by start**.

- Intervals that **overlap or merely touch** merge into one. Touching means they share an endpoint:
  `[1, 2]` and `[2, 3]` merge into `[1, 3]`.
- The input is **not** guaranteed to be sorted and may contain duplicates or fully-nested intervals.
- Return a new list of `[start, end]` lists. For empty input, return `[]`.

Examples:
- `merge_intervals([])` → `[]`
- `merge_intervals([[1, 3]])` → `[[1, 3]]`
- `merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]])` → `[[1, 6], [8, 10], [15, 18]]`
- `merge_intervals([[1, 4], [4, 5]])` → `[[1, 5]]`
- `merge_intervals([[1, 10], [2, 3]])` → `[[1, 10]]`
- `merge_intervals([[3, 4], [1, 2]])` → `[[1, 2], [3, 4]]`
