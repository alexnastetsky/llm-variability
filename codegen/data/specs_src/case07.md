# min_coins

Return the **minimum number of coins** whose values sum exactly to `amount`, given an **unlimited
supply** of each denomination in `coins`.

- `coins` is a list of integers; `amount` is an integer.
- If `amount` is `0`, return `0` (regardless of `coins`).
- If `amount` cannot be formed by any combination of the coins, return `-1`.
- **Raise `ValueError`** if `amount < 0`, or any coin is `<= 0`, or `coins` contains duplicates.
  (A valid `coins` is a list of distinct positive ints; it may be empty. Empty coins with
  `amount > 0` returns `-1`; empty coins with `amount == 0` returns `0`.)
- Denominations are **not** assumed sorted, and a greedy largest-coin-first strategy is **not**
  guaranteed correct — the answer must be exact (e.g. `coins=[1,3,4], amount=6` is `2`, using 3+3,
  not the greedy 4+1+1 = 3).
- Return a plain `int` (`-1` or a count `>= 0`).
