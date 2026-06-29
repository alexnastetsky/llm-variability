# Open-Ended Tasks: where output variability finally appears

**Question.** The first two experiments (fully-specified triage pipeline; fully-specified code
generation) found **no** behavioral variability and no gap between LLM-orchestrated (Option 1) and
code-orchestrated (Option 2) execution — concluding that variability comes from *decision freedom /
underspecification*, not from LLM orchestration per se. This experiment tests that directly by
**removing the specification**: tasks that admit many correct behaviors, each isolating one
ambiguity axis, plus multi-file tasks. Does behavioral divergence now appear, and does **LLM
orchestration produce more of it than code orchestration**?

**Finding (headline).** Divergence appears — **and only here** (the fully-specified control
`m2_roman`, and the two prior experiments, show none). At K=20 over 11 tasks (440 runs), **every
run was valid** (no wrong answers — only different *acceptable* choices). Divergence showed up on
**6 of the 11 tasks**, and **Option 1 (Claude Code) diverged on more axes than Option 2 — 5 tasks
vs 2** — the strongest support yet for the original hypothesis. The split is usually lopsided (the
model has a strong default convention it deviates from occasionally), and the divergence is in
*conventions and representation* — rounding mode, numeric type, output schema, truthy vocabulary —
never in the computed values.

---

## 1. Setup

- **Model / endpoint:** `databricks-claude-opus-4-8`, fixed sampling, same Databricks-hosted
  Anthropic endpoint and per-rep isolation as the other experiments.
- **Two architectures:** Option 1 (headless `claude -p` writes the solution file(s), runs the
  oracle, loops until valid, in isolation) vs Option 2 (deterministic harness; the LLM only
  generates source; bounded fix loop). Same model by construction.
- **11 tasks** (`data/cases.json`), **K=20** per task per condition (440 runs total):
  - **9 underspecified single-file tasks**, each isolating one ambiguity axis (see table).
  - **`m1_stats`** — a multi-file (`core.py`+`api.py`) underspecified task (a stats `summary` dict).
  - **`m2_roman`** — a multi-file **fully-specified control** (`to_roman`): one correct behavior.

## 2. Methodology — grading divergence, not correctness

There is no single correct answer, so grading flips:
- **Validity** — does the candidate satisfy a permissive per-task **contract** (`data/contracts/`)
  on every one of 200 seeded corpus inputs? This replaces "correctness."
- **Behavioral fingerprint** — a hash of the candidate's output vector over the fixed corpus. Same
  fingerprint = same behavior; **distinct fingerprints across runs = divergence**. The headline
  metric is the number of distinct fingerprints among valid runs (`analysis/metrics.py`); the
  diverging axis and split are auto-characterized by `analysis/divergence.py` (which replays one
  representative per behavior group and reports the first corpus input on which they disagree).
- A candidate is a directory of one or more files; the oracle imports the entry module in an
  isolated subprocess (multi-file solutions use absolute imports).

## 3. Results — diverging axis and split per task

Cells are `<distinct behaviors among valid runs> (split of the K=20 runs)`. Validity was **1.00**
on every task in both conditions.

| task | diverging axis | Option 1 | Option 2 |
|---|---|---|---|
| `u1_rank_items` | tie-break order among equal scores | 1 | 1 |
| `u2_round_all` | half-value rounding convention | **2** (19:1) | 1 |
| `u3_top_k` | order of the returned k largest | **2** (19:1) | 1 |
| `u4_dedup` | order / which duplicate kept | 1 | 1 |
| `u5_argmax` | index when the max is tied | 1 | 1 |
| `u6_median` | even-length convention / numeric type | **2** (15:5) | 1 |
| `u7_most_common` | which element when modes are tied | 1 | **2** (17:3) |
| `u8_top_k_indices` | indices on value ties + order | 1 | 1 |
| `u9_parse_bool` | truthy vocabulary (non-canonical strings) | **2** (19:1) | 1 |
| `m1_stats` (multi-file) | output schema / representation | **2** (10:10) | **4** (9:5:5:1) |
| `m2_roman` (control) | none — fully specified | 1 | 1 |

**Tasks that diverged: Option 1 → 5 (`u2,u3,u6,u9,m1`); Option 2 → 2 (`u7,m1`).**

**What diverged, concretely** (from `analysis/divergence.py`):
- **`u2_round_all`** (Opt 1): `4.5 → 4` (half-to-even, 19 runs) vs `4.5 → 5` (half-up, 1 run). A
  genuine *value* difference. Option 2 used one convention on all 20.
- **`u3_top_k`** (Opt 1): returned the k largest **sorted descending** (19) vs **in original input
  order** (1). An ordering choice.
- **`u6_median`** (Opt 1): odd-length median returned as **float `7.0`** (15) vs **int `7`** (5) —
  same value, different numeric *type*.
- **`u9_parse_bool`** (Opt 1): `"on" → True` (19) vs `"on" → False` (1) — a genuine semantic
  (vocabulary) difference on a non-canonical string.
- **`m1_stats`** (Opt 1): identical stats, but **with a `count` key** (10) vs **without** (10) — an
  output-schema choice; the most evenly split of any task.
- **`u7_most_common`** (Opt 2): mode-tie resolved to the **first-encountered** element (17) vs a
  **different tied element** (3). Notably this is the one task where **Option 2 diverged but Option
  1 did not**.
- **`m1_stats`** (Opt 2): four behaviors from crossing two representation choices — keys `min`/`max`
  vs `minimum`/`maximum`, and odd-length median `15.0` vs `15`.

## 4. Interpretation

1. **Underspecification is the source of variability — shown by construction, across many tasks.**
   Divergence appears only on underspecified tasks; the fully-specified control and both prior
   experiments are flat. This nails the cross-experiment thesis.
2. **LLM orchestration amplifies it (the hypothesis, supported).** Option 1 diverged on **5** axes
   to Option 2's **2**. Given the same model and tasks, the Claude Code agent makes inconsistent
   free-choices where the bare generation call is internally consistent (`u2,u3,u6,u9`). This is
   the effect the first two experiments were built to find and couldn't, because their tasks were
   fully specified.
3. **But it is a tendency, not a law.** `u7_most_common` is a counterexample: only **Option 2**
   diverged. And **4 of 9** single-axis tasks (`u1,u4,u5,u8`) never diverged in either condition —
   the model has a strong shared default for some choices (e.g. argmax → first index, dedup →
   first-seen order) and reliably picks it.
4. **Splits are lopsided; defaults are strong.** Most divergent tasks split ~19:1 or 15:5 — a
   dominant convention with occasional deviation — rather than a coin-flip. The exception is the
   multi-file schema task (`m1`, 10:10 / 9:5:5:1), where there is no single obvious packaging.
5. **The divergence is in conventions/representation, not correctness.** Validity was 1.00
   everywhere. What varied was *which* acceptable convention (rounding mode, truthy vocabulary),
   *how* a result was typed (`7` vs `7.0`), or *how* it was packaged (key names, extra keys) — the
   ungoverned surface, exactly as the triage experiment's free-text `summary`.
6. **Multi-file structure alone does not cause divergence** — the specified `m2_roman` control was
   1@1.00 in both conditions; divergence tracked underspecification, not file count.

## 5. Limitations / threats to validity

- **K=20, 11 tasks, one model.** Enough to show the effect and a clear Option-1 > Option-2 axis
  count (5 vs 2), but the per-task splits are noisy at K=20 and the rare deviations (the "1" in
  19:1) would need larger K to estimate reliably.
- **The contract defines "valid."** A stricter/looser contract changes validity, not the
  fingerprint counts. The contracts accept the obvious acceptable behaviors and key aliases.
- **Fingerprints are representation-sensitive** (e.g. `7` vs `7.0`, an extra `count` key count as
  distinct behaviors). That is intentional — output representation is observable behavior — but it
  means "divergence" includes representational, not only computational, differences. The
  per-axis characterization in §3 distinguishes the two.
- **Fix-loop asymmetry** (Option 1 model-driven, Option 2 fixed protocol) biases validity, not the
  divergence comparison among valid runs.

## 6. Reproduce

```bash
pip install -r ../requirements.txt
python3 tools/run_tests.py --selftest          # all 11 references satisfy their own contracts
source config/experiment.env
python3 option2/run_option2.py --check         # one generation/task; prints model + fingerprint

python3 option2/run_option2.py --reps 20 --workers 8 --out-dir "$PWD/results_full/option2"
OUT_ROOT="$PWD/results_full/option1_default" WORKERS=5 bash option1/run_option1.sh 20
python3 analysis/metrics.py     --results-root results_full   # validity / distinct behaviors / consistency
python3 analysis/divergence.py  --results-root results_full   # diverging axis + split, with examples
```

Run outputs (`results_full/`, including each run's saved solution directory) are git-ignored and
regenerated by the steps above.
