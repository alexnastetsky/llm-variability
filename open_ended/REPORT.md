# Output Variability on Underspecified Coding Tasks

**Question.** When a task leaves real decisions open, do repeated runs of the same model converge on
one behavior or diverge across several? And does it matter **who orchestrates** the work — an LLM
agent that drives its own generate-and-validate loop, versus a deterministic program that calls the
model only to generate code?

We compare two architectures on the same tasks, same model (`databricks-claude-opus-4-8`, fixed
sampling), same endpoint:

- **Option 1 — LLM-orchestrated.** A headless coding agent (Claude Code) reads the spec, writes the
  solution file(s), runs the validation tool, and fixes in a loop until it passes — the agent
  decides each step.
- **Option 2 — code-orchestrated.** A deterministic Python harness drives the loop and calls the
  model only to generate the source; a fixed protocol re-prompts on failure.

Each of **11 tasks** is run **K=20 times per architecture** (440 runs total). Every task is
deliberately **underspecified** along exactly one axis (e.g. how to break a tie, which rounding
convention), except one fully-specified control.

**Headline.** Every run produced a *valid* (acceptable) solution — there were no wrong answers.
What varied was *which* acceptable behavior. Divergence appeared on **6 of 11 tasks**, and the
**LLM-orchestrated agent (Option 1) diverged on more axes than the code-orchestrated harness
(Option 2): 5 tasks vs 2.** Splits are usually lopsided — a dominant default the model departs from
occasionally — and the differences are in *conventions and output representation* (rounding mode,
numeric type, schema, truthy vocabulary), never in the computed values.

---

## How divergence is measured

There is no single correct answer for an underspecified task, so each task ships:

- a permissive **contract** — a checker for whether an output is *acceptable* (e.g. for "rank by
  score", the result must be a permutation ordered by non-increasing score; tie order is free).
  **Validity** = the fraction of runs whose outputs satisfy the contract on every one of 200 fixed,
  seeded corpus inputs.
- a **behavioral fingerprint** — a hash of a run's output vector over that fixed corpus. Two runs
  with the same fingerprint chose the same behavior; **distinct fingerprints = the runs diverged**.

The headline number per task is the count of **distinct behaviors among valid runs** (1 = perfect
convergence). Each solution is run in an isolated subprocess; multi-file solutions are imported by
their entry module.

---

## Results per task

`behaviors` = distinct behaviors among the 20 valid runs; `split` = how the 20 runs distributed;
`consistency` = share in the most common behavior (1.00 = identical every run).

| task | what it does | diverging axis | Option 1 (LLM) | Option 2 (code) |
|---|---|---|---|---|
| `u1_rank_items` | rank names by score | tie-break order among equal scores | 1 @ 1.00 | 1 @ 1.00 |
| `u2_round_all` | round numbers to ints | half-value rounding convention | **2** (19:1) @ 0.95 | 1 @ 1.00 |
| `u3_top_k` | the k largest values | order of the returned values | **2** (19:1) @ 0.95 | 1 @ 1.00 |
| `u4_dedup` | remove duplicates | order / which occurrence kept | 1 @ 1.00 | 1 @ 1.00 |
| `u5_argmax` | index of the maximum | index when the max is tied | 1 @ 1.00 | 1 @ 1.00 |
| `u6_median` | the median | even-length convention / numeric type | **2** (15:5) @ 0.75 | 1 @ 1.00 |
| `u7_most_common` | most frequent value | which element when modes tie | 1 @ 1.00 | **2** (17:3) @ 0.85 |
| `u8_top_k_indices` | indices of the k largest | which indices on ties + order | 1 @ 1.00 | 1 @ 1.00 |
| `u9_parse_bool` | string → boolean | truthy vocabulary for odd strings | **2** (19:1) @ 0.95 | 1 @ 1.00 |
| `m1_stats` | summary-stats dict (2 files) | output schema / representation | **2** (10:10) @ 0.50 | **4** (9:5:5:1) @ 0.45 |
| `m2_roman` | integer → Roman numeral (2 files) | none — fully specified (control) | 1 @ 1.00 | 1 @ 1.00 |

**Diverged: Option 1 on 5 tasks (`u2, u3, u6, u9, m1`); Option 2 on 2 tasks (`u7, m1`).** Validity
was 1.00 on every task in both architectures. The fully-specified control (`m2_roman`) and four
single-axis tasks (`u1, u4, u5, u8`) showed no divergence at all.

---

## Examples of divergence

### `u2_round_all` — half-value rounding convention (Option 1: 19 vs 1)
Most runs round halves to even; one run rounds halves up.
```
input [6.0, 4.5, 8.75, 10.25, 3.0]
  19 runs -> [6, 4, 9, 10, 3]      # 4.5 -> 4  (round half to even)
   1 run  -> [6, 5, 9, 10, 3]      # 4.5 -> 5  (round half up)
```
*A genuine value difference.* Option 2 used one convention on all 20 runs.

### `u3_top_k` — order of the returned k largest (Option 1: 19 vs 1)
```
input nums=[0, 4, 2, 3, 4, 0, 5], k=7
  19 runs -> [5, 4, 4, 3, 2, 0, 0]   # sorted descending
   1 run  -> [0, 4, 2, 3, 4, 0, 5]   # left in original input order
```

### `u6_median` — numeric type of the result (Option 1: 15 vs 5)
The median *value* always agrees; the runs disagree on its **type** for odd-length inputs.
```
input [5, 11, 4, 7, 8]
  15 runs -> 7.0    (float)
   5 runs -> 7      (int)
```

### `u9_parse_bool` — truthy vocabulary for non-canonical strings (Option 1: 19 vs 1)
"true"/"false" are pinned; strings like "on"/"yes" are free.
```
input "on"            input "yes"
  19 runs -> true       19 runs -> true
   1 run  -> false       1 run  -> false
```

### `u7_most_common` — which element when modes tie (Option 2: 17 vs 3)
The only task where the **code-orchestrated** harness diverged but the LLM agent did not.
```
input [3, 2, 0, 2, 3, 0, 1]      # 3, 2, and 0 each appear twice
  17 runs -> 3      # first to reach the max count
   3 runs -> 2      # a different tied element
```

### `m1_stats` — output schema / representation (Option 1: 10 vs 10; Option 2: four behaviors)
The statistics agree numerically; the *returned dict* differs. The most evenly split task.
```
input [16, 6, 15]
Option 1:
  10 runs -> {"count": 3, "max": 16, "mean": 12.333…, "median": 15, "min": 6}   # adds a "count" key
  10 runs -> {           "max": 16, "mean": 12.333…, "median": 15, "min": 6}    # no "count" key
Option 2 (crossing two choices — key names × median type):
   9 runs -> {"max": …, "median": 15.0, "min": …}          # min/max,        median float
   5 runs -> {"maximum": …, "median": 15.0, "minimum": …}  # minimum/maximum, median float
   5 runs -> {"maximum": …, "median": 15,   "minimum": …}  # minimum/maximum, median int
   1 run  -> {"max": …, "median": 15,   "min": …}          # min/max,        median int
```

---

## Observations

1. **Underspecification, not the model's competence, is what lets variability appear.** Every run
   was valid; the fully-specified control never diverged. The model only "disagrees with itself"
   where the task genuinely leaves a choice open.
2. **The LLM-orchestrated agent diverges on more axes (5 vs 2).** Given the same task and model, the
   agent makes inconsistent free-choices (rounding mode, output order, numeric type, vocabulary)
   where the bare generation harness is internally consistent. Driving the task through an agent —
   with its own prompt, tools, and multi-step loop — adds variability to the unconstrained decisions.
3. **It is a tendency, not a rule.** `u7_most_common` diverged only under the code-orchestrated
   harness, and four single-axis tasks (`u1, u4, u5, u8`) never diverged in either architecture —
   the model has a strong, reliable default for some choices (e.g. argmax → first index, dedup →
   first-seen order).
4. **Splits are lopsided.** Most divergent tasks split ~19:1 or 15:5: a dominant convention with
   occasional deviation, not a coin flip. The exception is the multi-file summary-stats task, where
   there is no single obvious way to name keys or type the median.
5. **The variability is in conventions and representation, not correctness.** What changes between
   runs is *which* acceptable convention (half-even vs half-up), *how* a value is typed (`7` vs
   `7.0`), or *how* a result is packaged (key names, an extra `count` key) — never a wrong answer.

---

## Limitations

- **K=20, 11 tasks, one model.** Enough to demonstrate the effect and a clear Option-1 > Option-2
  axis count, but the rare deviations (the "1" in a 19:1 split) are noisy and would need larger K to
  estimate reliably.
- **The contract defines "valid."** A stricter or looser contract changes validity, not the
  behavior counts. The contracts here accept the obvious acceptable behaviors and common key aliases.
- **Fingerprints are representation-sensitive** — `7` vs `7.0`, or an extra dict key, count as
  distinct behaviors. That is intentional (output representation is observable behavior), but it
  means "divergence" includes representational, not only computational, differences; the per-task
  examples above make the distinction explicit.

---

## Reproduce

```bash
pip install -r ../requirements.txt
python3 tools/run_tests.py --selftest          # every reference solution satisfies its own contract
source config/experiment.env
python3 option2/run_option2.py --check         # one generation per task; prints the model id

python3 option2/run_option2.py --reps 20 --workers 8 --out-dir "$PWD/results_full/option2"
OUT_ROOT="$PWD/results_full/option1_default" WORKERS=5 bash option1/run_option1.sh 20
python3 analysis/metrics.py     --results-root results_full   # validity / distinct behaviors / consistency
python3 analysis/divergence.py  --results-root results_full   # diverging axis + split, with examples
```

Run outputs are regenerated by these steps.
