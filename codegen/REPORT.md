# Code-Generation Variability: LLM-Orchestrated vs. Code-Orchestrated (harder tasks)

**Question.** Does an LLM that *orchestrates* a generate→validate→fix loop (Option 1) produce more
**output variability** than deterministic code that *drives* the loop and calls the LLM only to emit
source (Option 2)? And the sharper question this round adds: does **raising task complexity** make
behavioral variability appear, where five trivial tasks earlier showed none?

**Finding (headline).** Across **200 runs** — 10 tasks × K=10 × two architectures, spanning five
genuinely hard tasks (a recursive-descent expression evaluator, coin-change DP, a stateful KV store
with nested transactions, a glob matcher, and a lexicographic topological sort) — **every run
produced behaviorally-identical, correct output** (behavioral consistency **1.00**, correctness
**1.00**, zero divergence) for **both** architectures. This held even though the **source text
varied on almost every run** (text consistency as low as **0.10** on the hard tasks) and even though
each task was posed under **3 different prompt variants**. The hypothesis was **not supported**, now
under much harder conditions: complexity drove *textual* variability sharply up but left *behavioral*
variability at zero.

---

## 1. Setup

- **Model / endpoint:** `databricks-claude-opus-4-8` (server reports `claude-opus-4-8`) via the
  Databricks-hosted native Anthropic Messages API, **fixed sampling** (Opus 4.8 exposes no
  temperature). Both options use the identical model by construction (`config/experiment.env`,
  `common/llm_client.py`).
- **Two architectures:**
  - **Option 1 — LLM orchestrates:** headless `claude -p` reads the spec, writes a solution file,
    runs the oracle, and fixes in a loop until the named tests pass. Strict isolation per rep (fresh
    `CLAUDE_CONFIG_DIR`, inline auth, `--setting-sources user`, explicit `--settings`, empty
    `--mcp-config`, `--allowedTools` = `Read`/`Write`/`Bash(python3 tools/run_tests.py:*)`,
    `--no-session-persistence`). The harness — not the model — runs the oracle afterward to write
    the authoritative graded record.
  - **Option 2 — code orchestrates:** a deterministic Python harness; the LLM is called **only** to
    generate the source. A bounded fix loop (`MAX_ATTEMPTS=3`, re-prompting with the named failures)
    mirrors Option 1's loop so both iterate — the contrast is *who drives the loop*.
- **Workload — 10 single-function tasks** (`data/cases.json`), each pure and deterministic:
  - *Trivial baseline* (case01–05): `roman_to_int`, `merge_intervals`, `balanced_parens`,
    `run_length_encode`, `int_to_base`.
  - *Harder tier* (case06–10): `eval_expr` (truncated-division arithmetic parser), `min_coins`
    (coin-change DP), `kv_store_ops` (nested transactions), `wildcard_match` (glob DP), `topo_sort`
    (lexicographically-smallest order). Each pins every ambiguity (error type, tie-break,
    truncation, degenerate inputs) so there is exactly one correct behavior per input.
- **Prompt variants ("different inputs for the same task"):** each task has 3 semantically
  identical spec variants (same authored rules, different worked examples + intro wording, generated
  from the verified tests by `tools/build_specs.py`). Reps cycle through variants by index, so
  consistency is measured across prompt framings, not one fixed prompt.
- **Scale:** K=10 per task per condition → 100 runs/condition, 200 total.

## 2. Methodology

- **Three grading altitudes** (`analysis/metrics.py`), per condition×case over K runs:
  - **text** — hash of raw generated source;
  - **structural** — hash of the AST-normalized source (docstrings/comments/formatting stripped);
  - **behavioral** *(primary)* — `(status, named-test result vector, differential-corpus output
    hash)`; invariant to source text. This is the code-gen analogue of the triage experiment's
    structured-field tuple.
- **Behavioral oracle** (`tools/run_tests.py`): runs each candidate in an **isolated subprocess**
  (rlimits, wall-clock timeout, `PYTHONHASHSEED=0`, temp `cwd`) behind a static AST pre-check
  (allowlisted imports; `open`/`eval`/`exec`/`__import__` banned). It grades against the named tests
  **and** a fixed **seeded differential corpus** (~300 inputs/case) compared element-by-element to a
  hidden reference. **Correctness = all named tests pass AND matches the reference on every corpus
  input.** Named tests can assert exceptions via a `{"__raises__": "..."}` sentinel.
- The free-form artifact (the source) is what the prior triage experiment couldn't grade; here it is
  graded by **behavior**, the property that actually matters.

## 3. Results

**Consistency by altitude (mean over 10 cases):**

| condition | text | struct | behavioral | correctness |
|---|---|---|---|---|
| Option 1 (Claude Code orchestrates) | 0.42 | 0.44 | **1.00** | **1.00** |
| Option 2 (code orchestrates) | 0.40 | 0.43 | **1.00** | **1.00** |

**Per-case behavioral consistency was 1.00 for all 10 tasks in both conditions.** The variability
lived entirely at the text/structural altitudes, and most on the hard tasks:

| | case01 | case02 | case03 | case04 | case05 | case06 | case07 | case08 | case09 | case10 |
|---|---|---|---|---|---|---|---|---|---|---|
| **text** (Opt 1) | 0.40 | 0.90 | 1.00 | 0.50 | 0.70 | 0.10 | 0.20 | 0.10 | 0.20 | 0.10 |
| **text** (Opt 2) | 0.50 | 0.80 | 0.40 | 0.40 | 0.70 | 0.10 | 0.30 | 0.10 | 0.60 | 0.10 |
| **behavioral** (both) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

Mean text consistency: **trivial tasks ≈ 0.6–0.7** vs **hard tasks ≈ 0.1–0.2** — i.e. on hard tasks
the model wrote a *different* implementation on almost every run, yet all were behaviorally
identical and correct.

**Per-prompt-variant** (`analysis/by_variant.py`): within every (case, variant) cell, behavioral
consistency = **1.00** and correctness = **1.00** for all three variants in both conditions — prompt
framing did not change behavior.

**Failure signatures:** none. No `wrong_on_corpus`, `partial_pass`, `timeout`, `blocked`, or wrong
exception type occurred in any of the 200 runs.

**Fix-loop activity:** Option 2 reached a correct solution in one generation on 89/100 runs and used
a 2nd attempt on 11/100 (the bounded loop repaired the rest). Option 1 looped internally to PASS on
every run (its internal iteration count is not captured — see Limitations).

**Illustrative — same behavior, different code.** Two Option 1 `eval_expr` solutions (different
prompt variants) share the identical `behavior_sha 803fbdb…` while differing structurally: one
threads the parser cursor through a one-element list (`pos = [0]`) and tags integer tokens as
`('int', n)` tuples; the other uses `nonlocal pos` and bare-int tokens. Different programs, identical
function.

## 4. Interpretation

1. **Complexity raised textual variability, not behavioral variability.** Harder, more open-ended
   tasks produced many distinct implementations (text consistency ↓ to 0.10), yet the behavioral
   altitude stayed pinned at 1.00. The model converges on the *same correct function* while
   expressing it differently almost every time.
2. **The hypothesis is still not supported — now under harder conditions.** LLM-orchestrated
   generation was exactly as behaviorally consistent (1.00) as code-orchestrated generation. There
   is no orchestration-driven behavioral variability gap on these tasks.
3. **Prompt variation didn't introduce behavioral variability either.** Three different framings of
   each task yielded the same correct behavior every time.
4. **Consistent with the triage finding, and sharper.** When the graded output is well-specified and
   has a deterministic correct answer — even a complex one reached via free-form code — a
   fixed-sampling reasoning model is effectively deterministic *in behavior*. Variability lives in
   the ungoverned surface (source text), exactly as the triage experiment's free-text `summary` did.

## 5. Limitations / threats to validity

- **Oracle/corpus completeness.** Behavioral equivalence is approximated by ~300 seeded inputs vs a
  reference; two genuinely different functions agreeing on all corpus inputs would hash identically.
  The named suites are deliberately strong (they include the classic wrong-approach traps), so a
  subtle `wrong_on_corpus` could in principle still escape detection.
- **K=10.** Enough to show the effect, but a far smaller bound than the triage experiment's K=200.
  No divergence appeared in 200 runs, but the upper bound on a rare divergence rate is loose.
- **Fix-loop asymmetry.** Both options loop, but Option 1's is model-driven and Option 2's is a fixed
  protocol; this biases *correctness*, not behavioral consistency among passing runs (which was 1.00
  regardless). Option 1's internal attempt count is not recorded (`_attempts` is null for Option 1).
- **One model, one task family.** All Python, pure functions, fully-specified. Underspecified or
  multi-file tasks — where legitimate behavioral choices exist — remain the place most likely to
  surface real behavioral variability and are the natural next experiment.
- **Sandbox is defense-in-depth, not a jail** (rlimits + temp cwd + AST pre-check; stdlib can't
  hard-block network). Tasks are pure and were run locally.

## 6. Reproduce

```bash
pip install -r ../requirements.txt            # anthropic; rest is stdlib

python3 tools/run_tests.py --selftest         # all 10 references pass own oracle + corpus
python3 tools/run_tests.py --build-cache       # freeze reference corpus vectors
python3 tools/build_specs.py                   # (re)generate the 3 prompt variants per task

source config/experiment.env
python3 option2/run_option2.py --check         # one generation/case; prints model=claude-opus-4-8

# full run (K=10, all 10 tasks, both options)
python3 option2/run_option2.py --reps 10 --workers 8 --out-dir "$PWD/results_full/option2"
OUT_ROOT="$PWD/results_full/option1_default" WORKERS=5 bash option1/run_option1.sh 10

python3 analysis/metrics.py     --results-root results_full   # 3-altitude table
python3 analysis/by_variant.py  --results-root results_full   # per-prompt-variant breakdown
```

Run outputs (`results_full/`, generated `.solution.py` files, the corpus cache) are git-ignored and
regenerated by the steps above.
