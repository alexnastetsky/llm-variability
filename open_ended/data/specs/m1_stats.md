# stats library (two files)

Implement a small statistics library across **two files**:

- `core.py` — computation helpers.
- `api.py` — imports from `core` (use an absolute import, e.g. `from core import ...`)
  and exposes the entry function:

  `def summary(nums: list) -> dict`

`summary` takes a **non-empty** list of numbers and returns a dict of summary
statistics including at least the **mean**, **median**, **minimum**, and **maximum**.
