# Open-Ended Tasks: where output variability finally appears

**Question.** The first two experiments (fully-specified triage pipeline; fully-specified code
generation) found **no** behavioral variability and no gap between LLM-orchestrated (Option 1) and
code-orchestrated (Option 2) execution. Their shared conclusion: variability comes from *decision
freedom / underspecification*, not from LLM orchestration per se. This experiment tests that
directly by **removing the specification** — using tasks that admit *many* correct behaviors — and
asks: does behavioral divergence now appear, and does **LLM orchestration produce more of it than
code orchestration**?

**Finding (headline).** Divergence finally appears — **and only here.** On underspecified tasks,
runs made *different valid choices*; on the fully-specified control (`m2_roman`) and in the two
prior experiments, they did not. Crucially, **Option 1 (Claude Code orchestrates) diverged more
than Option 2 (code orchestrates)** on 2 of 3 single-file underspecified tasks — the **first
evidence supporting the original hypothesis**. The divergence is concentrated in *conventions and
output representation* (rounding mode, dict key names, int-vs-float), not correctness: **every one
of the 100 runs was valid** (satisfied the task contract).

---

## 1. Setup

- **Model / endpoint:** `databricks-claude-opus-4-8`, fixed sampling, same Databricks-hosted
  Anthropic endpoint and isolation discipline as the other experiments.
- **Two architectures:** Option 1 (headless `claude -p` writes the solution file(s), runs the
  oracle, loops until valid, in strict isolation) vs Option 2 (deterministic harness; the LLM only
  generates source; bounded fix loop). Same model by construction.
- **5 tasks** (`data/cases.json`), K=10 per task per condition (100 runs total):
  - **Underspecified, single-file:** `rank_items` (rank by score; **tie order unspecified**),
    `round_all` (round to nearest; **half-rounding unspecified**), `top_k` (k largest; **output
    order unspecified**).
  - **Multi-file, underspecified:** `m1_stats` — a two-file package (`core.py` + `api.py`) exposing
    `summary(nums)`; **key names, median-even convention, mean rounding, extra keys all free**.
  - **Multi-file, fully-specified (control):** `m2_roman` — a two-file package exposing
    `to_roman(n)`; exactly one correct behavior. Tests whether multi-file *structure alone* induces
    divergence (it should not).

## 2. Methodology — grading divergence, not correctness

There is no single correct answer for an underspecified task, so the grading model flips:
- **Validity** — does the candidate satisfy a permissive task **contract** (`data/contracts/`) on
  every one of ~200 seeded corpus inputs? (e.g. `rank_items`: output is a permutation ordered by
  non-increasing score — *ties in any order*; `round_all`: each value rounds to a neighbor, halves
  either way). This replaces "correctness."
- **Behavioral fingerprint** — a hash of the candidate's output vector over the fixed seeded corpus.
  Two runs with the **same** fingerprint chose the same behavior; **different** fingerprints means
  the runs *diverged* on the free choices. The headline metric is the number of **distinct
  fingerprints among valid runs** (`analysis/metrics.py`).
- The oracle (`tools/run_tests.py`) runs each candidate — a directory of one or more files — in an
  isolated subprocess, importing the entry module (multi-file solutions use absolute imports).

## 3. Results

**Distinct behaviors among valid runs (K=10), and modal behavioral consistency:**

| task | mode | Option 1 | Option 2 |
|---|---|---|---|
| `u1_rank_items` | underspecified | **2** @ 0.90 | 1 @ 1.00 |
| `u2_round_all` | underspecified | **2** @ 0.70 | 1 @ 1.00 |
| `u3_top_k` | underspecified | 1 @ 1.00 | 1 @ 1.00 |
| `m1_stats` | multi-file, underspecified | **3** @ 0.50 | **3** @ 0.60 |
| `m2_roman` | multi-file, **specified** (control) | 1 @ 1.00 | 1 @ 1.00 |

Validity was **1.00 everywhere** (all 100 runs produced acceptable output). Mean distinct behaviors:
Option 1 **1.8** vs Option 2 **1.4**; mean behavioral consistency Option 1 **0.82** vs Option 2
**0.92** — Option 1 is *less* consistent (more divergent).

**What diverged, concretely:**
- **`u2_round_all` (Option 1):** split between **banker's rounding** (half-to-even — `0.5→0`,
  `2.5→2`; 7 runs) and **half-up** (`0.5→1`, `2.5→3`; 3 runs). Option 2 used one convention on all
  10 runs. A textbook underspecified choice, resolved inconsistently only under LLM orchestration.
- **`u1_rank_items` (Option 1):** two tie-break behaviors (9 vs 1), differing on a minority of
  corpus inputs; Option 2 converged on one.
- **`m1_stats` (both):** three behaviors, driven by **output representation** — dict keys
  `min`/`max` vs `minimum`/`maximum`, and odd-length median typed as int `5` vs float `5.0`. The
  underlying statistics agreed numerically; the *returned objects* differed.
- **`u3_top_k`, `m2_roman`:** no divergence — the model has a single strong default for output
  order, and the specified control is correct-and-identical every time.

## 4. Interpretation

1. **Underspecification is the source of variability — now shown by construction.** Removing the
   spec is exactly what makes behavioral divergence appear; the fully-specified control and the two
   prior experiments show none. This confirms the cross-experiment thesis directly.
2. **LLM orchestration amplifies it (first hypothesis support).** Given the *same* underspecified
   task and the *same* model, the Claude Code agent (Option 1) made different free-choices across
   runs where the bare generation call (Option 2) was internally consistent (`u1`, `u2`). The
   agentic context — system prompt, tools, multi-step loop — appears to inject additional
   variability into the unconstrained decisions. This is the divergence the first two experiments
   were built to find and didn't, because their tasks were fully specified.
3. **The divergence is in conventions, not correctness.** Every run was valid. What varied was
   *which* acceptable convention (rounding mode) or *how* the result was packaged (key names, numeric
   type) — the ungoverned surface, again, exactly as the triage experiment's free-text `summary`.
4. **Multi-file structure alone does not cause divergence.** The specified two-file control
   (`m2_roman`) was 1@1.00 in both conditions; divergence tracked *underspecification*, not file count.

## 5. Limitations / threats to validity

- **K=10, 5 tasks, one model.** Enough to demonstrate the effect and an Option-1 vs Option-2 gap,
  but the gap is modest (1.8 vs 1.4 distinct behaviors) and would benefit from larger K and more
  tasks before quantifying it.
- **Contract permissiveness defines "valid."** A stricter or looser contract would change validity
  (not the fingerprint counts). The contracts here accept the obvious acceptable behaviors and key
  aliases; they encode the author's judgment of "acceptable."
- **Behavioral equivalence is approximated** by the seeded corpus, and fingerprints are sensitive to
  representation (e.g. `5` vs `5.0` count as different behaviors). That sensitivity is intentional
  here — output representation is a real, observable behavior — but it means "divergence" includes
  cosmetic-but-observable differences, not only differing computations.
- **Fix-loop asymmetry** (Option 1 model-driven, Option 2 fixed protocol) biases validity, not the
  divergence comparison among valid runs.

## 6. Reproduce

```bash
pip install -r ../requirements.txt
python3 tools/run_tests.py --selftest          # all 5 references satisfy their own contracts
source config/experiment.env
python3 option2/run_option2.py --check         # one generation/task; prints model + fingerprint

python3 option2/run_option2.py --reps 10 --workers 6 --out-dir "$PWD/results_full/option2"
OUT_ROOT="$PWD/results_full/option1_default" WORKERS=5 bash option1/run_option1.sh 10
python3 analysis/metrics.py --results-root results_full
```

Run outputs (`results_full/`, including each run's saved solution directory) are git-ignored and
regenerated by the steps above.
