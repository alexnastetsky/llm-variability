# Output Variability on Underspecified Coding Tasks

**Question.** When a coding task leaves a real decision open, do repeated runs of the same model
converge on one behavior or diverge across several? And does it matter **who orchestrates** the
work — an LLM agent that drives its own write-and-validate loop, versus a deterministic program
that calls the model only to generate code?

Two architectures are compared on the same tasks, same model (`databricks-claude-opus-4-8`, fixed
sampling), same endpoint. In **both**, the model writes a *program*; the harness then **executes**
it on a fixed input corpus and grades the execution output.

- **Option 1 — LLM-orchestrated.** A headless coding agent reads the spec, writes the solution
  file(s), runs the validation tool, and fixes in a loop until it passes — the agent decides each step.
- **Option 2 — code-orchestrated.** A deterministic harness drives the loop and calls the model only
  to generate the source; a fixed protocol re-prompts on failure.

**18 tasks**, **K=30 runs per architecture** (1080 runs total). 16 tasks are deliberately
**underspecified** along one axis (e.g. how to break a tie, which rounding rule, how to format an
output); **2 are fully-specified controls** (marked **CONTROL** below) that should converge.

**Headline.** Every run produced a *valid* (acceptable) solution — no wrong answers. What varied was
*which* acceptable behavior. Divergence appeared on **6 of the 16 underspecified tasks**; the
**LLM-orchestrated agent (Option 1) diverged on more axes than the code-orchestrated harness — 5 vs
4** (overlapping on the richest task). Both controls converged perfectly. Separately, the
LLM-orchestrated agent was **~7× slower per run** (≈34s vs ≈5s). Divergence is always in
*conventions and representation* (rounding mode, numeric type, output schema, capitalization),
never in the computed values.

---

## How divergence is measured

Each task ships:

- a permissive **contract** — a checker for whether an output is *acceptable* (e.g. for "rank by
  score", the result must be a permutation ordered by non-increasing score; tie order is free).
  **Validity** = the fraction of runs whose outputs satisfy the contract on every one of 200 fixed,
  seeded corpus inputs.
- a **behavioral fingerprint** — a hash of a run's output vector over that fixed corpus. Two runs
  with the same fingerprint chose the same behavior; **distinct fingerprints = the runs diverged**.

The headline number per task is the count of **distinct behaviors among valid runs** (1 = perfect
convergence). Solutions run in an isolated subprocess; multi-file solutions are imported by entry module.

---

## Results per task

`behaviors` = distinct behaviors among the 30 valid runs; `(split)` = how the 30 runs distributed;
`@consistency` = share in the most common behavior. Validity was **1.00** for every task in both
architectures.

| task | diverging axis | Option 1 (LLM) | Option 2 (code) |
|---|---|---|---|
| `u1_rank_items` | tie-break order among equal scores | 1 @ 1.00 | 1 @ 1.00 |
| `u2_round_all` | half-value rounding convention | **2** (28:2) @ 0.93 | 1 @ 1.00 |
| `u3_top_k` | order of the returned k largest | 1 @ 1.00 | 1 @ 1.00 |
| `u4_dedup` | order / which duplicate kept | 1 @ 1.00 | 1 @ 1.00 |
| `u5_argmax` | index when the max is tied | 1 @ 1.00 | 1 @ 1.00 |
| `u6_median` | even-length convention / numeric type | **2** (24:6) @ 0.80 | 1 @ 1.00 |
| `u7_most_common` | which element when modes tie | 1 @ 1.00 | **2** (24:6) @ 0.80 |
| `u8_top_k_indices` | indices on value ties + order | 1 @ 1.00 | **2** (29:1) @ 0.97 |
| `u9_parse_bool` | truthy vocabulary for odd strings | 1 @ 1.00 | 1 @ 1.00 |
| `u10_stats` *(multi-file)* | output schema / representation | **2** (22:8) @ 0.73 | **5** (14:7:6:2:1) @ 0.47 |
| `u11_titlecase` *(text)* | which words are capitalized | **2** (29:1) @ 0.97 | **2** (29:1) @ 0.97 |
| `u12_slugify` *(text)* | word separator / punctuation | 1 @ 1.00 | 1 @ 1.00 |
| `u13_initials` *(text)* | initials formatting (periods/spacing) | 1 @ 1.00 | 1 @ 1.00 |
| `u14_camel_to_snake` *(text)* | where to split acronym runs | **2** (27:3) @ 0.90 | 1 @ 1.00 |
| `u15_normalize_whitespace` *(text)* | trim ends + collapse | 1 @ 1.00 | 1 @ 1.00 |
| `u16_strip_punctuation` *(text)* | which punctuation removed | 1 @ 1.00 | 1 @ 1.00 |
| `ctl1_roman` — **CONTROL** *(multi-file)* | none — fully specified | 1 @ 1.00 | 1 @ 1.00 |
| `ctl2_reverse` — **CONTROL** *(text)* | none — fully specified | 1 @ 1.00 | 1 @ 1.00 |

**Diverged: Option 1 on 5 tasks (`u2, u6, u10, u11, u14`); Option 2 on 4 tasks (`u7, u8, u10, u11`).**
Both **CONTROL** tasks converged at `1 @ 1.00` in both architectures, and 9 of the 16 underspecified
tasks showed no divergence at all.

---

## Examples of divergence

### `u11_titlecase` *(text)* — which words are capitalized (both architectures: 29 vs 1)
```
input "river a of report"
  29 runs -> "River A Of Report"   # capitalize every word
   1 run  -> "River a of Report"   # lowercase the small words (a, of)
```

### `u14_camel_to_snake` *(text)* — where to split acronym runs (Option 1: 27 vs 3)
```
input "dataXMLValueData"
  27 runs -> "data_x_m_l_value_data"   # split every capital, even within "XML"
   3 runs -> "data_xml_value_data"     # keep the acronym "XML" together
```

### `u2_round_all` — half-value rounding (Option 1: 28 vs 2)
```
input [6.0, 4.5, 8.75, 10.25, 3.0]
  28 runs -> [6, 4, 9, 10, 3]    # 4.5 -> 4 (round half to even)
   2 runs -> [6, 5, 9, 10, 3]    # 4.5 -> 5 (round half up)
```
*A genuine value difference.* Option 2 used one convention on all 30 runs.

### `u6_median` — numeric type of the result (Option 1: 24 vs 6)
The median *value* always agrees; runs disagree on its **type** for odd-length inputs.
```
input [5, 11, 4, 7, 8]
  24 runs -> 7.0  (float)
   6 runs -> 7    (int)
```

### `u7_most_common` — which element when modes tie (Option 2: 24 vs 6)
```
input [3, 2, 0, 2, 3, 0, 1]      # 3, 2, and 0 each appear twice
  24 runs -> 3      # first to reach the max count
   6 runs -> 2      # a different tied element
```

### `u10_stats` *(multi-file)* — output schema / representation (Option 1: 2 behaviors; Option 2: 5)
The statistics agree numerically; the *returned dict* differs (key names, median type, an extra `count`).
```
input [16, 6, 15]
Option 1:
  22 runs -> {"maximum": 16, "mean": 12.33…, "median": 15, "minimum": 6}
   8 runs -> {"max": 16,     "mean": 12.33…, "median": 15, "min": 6}
Option 2 (five behaviors — crossing key names × median int/float × an extra key):
  14 runs -> {"max": …,     "median": 15.0, "min": …}
   7 runs -> {"maximum": …, "median": 15,   "minimum": …}
   6 runs -> {"maximum": …, "median": 15.0, "minimum": …}
   2 runs -> {"max": …,     "median": 15,   "min": …}
   1 run  -> {"count": 3, "maximum": …, "median": 15, "minimum": …}
```

### `u8_top_k_indices` — index order on value ties (Option 2: 29 vs 1)
```
input nums=[4, 3, 4, 2, 4, 4, 5, 4], k=8   # many tied 4s
  29 runs -> [6, 0, 2, 4, 5, 7, 1, 3]   # one ordering of the tied indices
   1 run  -> [6, 7, 5, 4, 2, 0, 1, 3]   # a different ordering
```

---

## Runtime: Option 1 is ~7× slower per run

Driving each task through an LLM agent (Option 1) costs far more wall-clock than a single
generation call (Option 2), because each Option 1 run is a full agent session — system prompt, tool
calls, and a multi-turn validate-and-fix loop — versus one API round-trip plus deterministic checks.

**Per-run latency (sequential, one worker, system idle):**

| task | Option 1 (LLM) | Option 2 (code) |
|---|---|---|
| `u6_median` | 25.8s | 4.0s |
| `u11_titlecase` | 39.6s | 3.8s |
| `u10_stats` (multi-file) | 25.8s | 9.0s |
| `ctl2_reverse` (trivial control) | 43.6s | 2.3s |
| **mean** | **≈ 33.7s** | **≈ 4.7s** |

Option 1's cost is dominated by **fixed agent overhead**, not task difficulty — the trivial
`reverse_string` control still took ~44s under the agent (vs 2.3s) because it pays the same
session-startup and tool-round-trip cost as any other task.

**At scale (the full K=30 run, 540 runs each):** Option 1 took **≈ 66 minutes** (6 parallel
workers); Option 2 took **≈ 5.3 minutes** (8 parallel workers) — a ~12× wall-clock gap end to end
(the per-run figure above is the cleaner architecture comparison, since the two runs used different
worker counts).

---

## Observations

1. **Underspecification, not the model's competence, is what lets variability appear.** Every run
   was valid; both controls converged at `1@1.00`. The model only "disagrees with itself" where the
   task genuinely leaves a choice open.
2. **The LLM-orchestrated agent diverges on more axes (5 vs 4).** Given the same task and model, the
   agent makes inconsistent free-choices (rounding mode, numeric type, acronym splitting, schema)
   where the bare generation harness is more often internally consistent. Driving a task through an
   agent — with its prompt, tools, and multi-step loop — adds variability to unconstrained decisions.
3. **It is a tendency, not a rule.** Two tasks (`u7`, `u8`) diverged only under the code-orchestrated
   harness, and 9 of 16 underspecified tasks never diverged in either architecture — the model has a
   strong, reliable default for many choices (e.g. argmax → first index, dedup → first-seen order,
   slug separator → `-`).
4. **Splits are lopsided.** Most divergent tasks split heavily (28:2, 29:1, 27:3): a dominant
   convention with occasional deviation, not a coin flip. The exception is the multi-file
   summary-stats task, where there is no single obvious way to name keys or type the values
   (Option 2 produced five distinct output schemas).
5. **Text tasks behave like the numeric ones.** Divergence shows up where text has a genuine open
   choice — capitalizing small words (`titlecase`), splitting acronym runs (`camel_to_snake`) —
   and not where the model has a firm default (`slugify`, `initials`, `normalize_whitespace`,
   `strip_punctuation` all converged).
6. **The variability is in conventions and representation, not correctness.** What changes between
   runs is *which* acceptable convention (half-even vs half-up), *how* a value is typed (`7` vs
   `7.0`), or *how* a result is packaged (key names, an extra field) — never a wrong answer.

---

## Limitations

- **K=30, 18 tasks, one model.** Enough to demonstrate the effect and an Option-1 > Option-2 axis
  count, but the rare deviations (the "2" in 28:2, the "1" in 29:1) are noisy; some tasks that split
  at smaller K converged here, and vice-versa, so individual splits shouldn't be over-read.
- **The contract defines "valid."** A stricter or looser contract changes validity, not the behavior
  counts. The contracts accept the obvious acceptable behaviors and common key aliases.
- **Fingerprints are representation-sensitive** — `7` vs `7.0`, or an extra dict key, count as
  distinct behaviors. That is intentional (output representation is observable behavior), but it
  means "divergence" includes representational, not only computational, differences; the per-task
  examples above make the distinction explicit.
- **Runtime depends on the agent and tooling**, not only the model; the ~7× figure reflects this
  agent's session/tool overhead and would shift with a lighter or heavier harness.

---

## Reproduce

```bash
pip install -r ../requirements.txt
python3 tools/run_tests.py --selftest          # every reference solution satisfies its own contract
source config/experiment.env
python3 option2/run_option2.py --check         # one generation per task; prints the model id

python3 option2/run_option2.py --reps 30 --workers 8 --out-dir "$PWD/results_full/option2"
OUT_ROOT="$PWD/results_full/option1_default" WORKERS=6 bash option1/run_option1.sh 30
python3 analysis/metrics.py     --results-root results_full   # validity / distinct behaviors / consistency
python3 analysis/divergence.py  --results-root results_full   # diverging axis + split, with examples
```

Run outputs are regenerated by these steps.
