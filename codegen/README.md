# Code-Generation Variability: LLM-orchestrated vs. code-orchestrated

The second experiment in this repo (see the [top-level README](../README.md)). Same hypothesis as
[`first_attempt/`](../first_attempt/) — does an LLM that **orchestrates** produce more output
variability than deterministic code that **drives** and calls the LLM only for a narrow sub-task? —
but the workload is **generating a Python function and validating it by execution**.

📄 **Results: [`REPORT.md`](REPORT.md).** Across 200 runs (10 tasks × K=10 × both architectures,
including 5 hard tasks, under 3 prompt variants each), behavioral consistency and correctness were
**1.00** for both architectures — even though source text varied on nearly every run (text
consistency as low as 0.10 on hard tasks). Complexity raised *textual* variability sharply but left
*behavioral* variability at zero; the hypothesis remained unsupported.

## Why this workload

The triage experiment graded a fixed structured schema and found perfect consistency. The one
field it *couldn't* grade — the free-text `summary` — varied on nearly every run, but free text has
no deterministic ground truth. **Generated code is the missing middle:** its surface is prose-like
(it varies run to run) yet, unlike prose, it has a **behavioral oracle** — compile it and run it.
So we can grade a free-form artifact by *what it does*, and we measure variability at three
altitudes:

- **text** — raw source hash (expected to vary a lot);
- **structural** — AST-normalized (docstrings/comments/formatting stripped), then hashed;
- **behavioral** *(primary)* — the vector of `(named-test results, differential-corpus output)`,
  invariant to source text. This is the analogue of the triage gradeable-field tuple.

Code generation also restores real **decision freedom** (many valid implementations), making it the
sharper test of where orchestration variability might appear.

## The two architectures

- **Option 1 — LLM orchestrates** (`option1/`): headless `claude -p` reads the spec, writes a
  solution file, runs the oracle, and fixes in a loop until the named tests pass. Strict isolation
  (fresh `CLAUDE_CONFIG_DIR`, inline auth, `--setting-sources user`, explicit `--settings`, empty
  `--mcp-config`, `--allowedTools` = `Read`/`Write`/`Bash(python3 tools/run_tests.py:*)`,
  `--no-session-persistence`). The **harness**, not the model, runs the oracle afterward to write
  the authoritative graded record.
- **Option 2 — code orchestrates** (`option2/run_option2.py`): deterministic harness; the LLM is
  called **only** to generate the source. A bounded, fixed-protocol fix loop (`MAX_ATTEMPTS=3`,
  re-prompting with the named failures) mirrors Option 1's loop so both iterate — the contrast is
  *who drives the loop*, not whether one exists.

Both use the same model/endpoint (`databricks-claude-opus-4-8`, fixed sampling) via the copied
`config/experiment.env` + `common/llm_client.py`.

## The 10 tasks

Small, pure, deterministic functions, each with hidden reference solution + named-test suite,
registered in `data/cases.json`:

- **Trivial baseline** (case01–05): `roman_to_int`, `merge_intervals`, `balanced_parens`,
  `run_length_encode`, `int_to_base`.
- **Harder tier** (case06–10): `eval_expr` (truncated-division arithmetic parser), `min_coins`
  (coin-change DP), `kv_store_ops` (nested transactions), `wildcard_match` (glob DP), `topo_sort`
  (lexicographically-smallest order). Each pins every ambiguity so there is one correct behavior.

**Prompt variants.** Each task has 3 semantically-identical spec variants (`data/specs/<case>/v*.md`,
generated from the authored rules in `data/specs_src/` + the verified tests by `tools/build_specs.py`).
Reps cycle through variants so consistency is measured across prompt framings, not one fixed prompt.

## The oracle (`tools/run_tests.py`)

Runs a candidate in an **isolated subprocess** (never in-process) against the named tests **and** a
fixed, seeded **differential-testing corpus** (≈300 inputs/case, `tools/corpus.py`) compared
element-by-element against the reference. Correctness = *all named tests pass AND matches the
reference on the corpus*. Safety: a static AST pre-check rejects `open`/`eval`/`exec`/`__import__`
and non-allowlisted imports before running; the subprocess sets `RLIMIT_CPU`/`RLIMIT_FSIZE` (and
`RLIMIT_AS` off macOS), a wall-clock timeout, `PYTHONHASHSEED=0`, and `cwd` in a temp dir without
`data/`. The CLI reveals only failing **named** tests (never the corpus answer key).

## Layout

```
data/cases.json            registry: func_name, signature, corpus_seed, timeout_s, n_variants
data/specs_src/*.md        authored rules per task (one per case)
data/specs/<case>/v*.md    generated prompt variants shown to the model
data/reference/*.py        hidden gold solutions (never shown to orchestrators)
data/tests/*.py            hidden named test suites: TESTS = [(args, expected | {"__raises__": X}), ...]
tools/corpus.py            seeded differential-testing input generators
tools/_runner.py           subprocess entrypoint: import candidate, call func on inputs
tools/run_tests.py         oracle: evaluate() + CLI + --selftest + --build-cache
tools/build_specs.py       generate the per-task prompt variants from rules + verified tests
tools/record_run.py        build the graded run JSON from final source + oracle
option1/                   Claude Code runner: task_prompt.md, settings.json, run_*.sh
option2/run_option2.py     deterministic harness; LLM only generates; bounded fix loop
analysis/ground_truth.py   gold_behavior(): reference behavior = the correct identity
analysis/metrics.py        consistency / entropy / correctness at all 3 altitudes
analysis/by_variant.py     per-prompt-variant behavioral breakdown
config/, common/           copied from first_attempt (self-contained)
```

## Reproduce

```bash
pip install -r ../requirements.txt          # anthropic; rest is stdlib

# offline sanity (no LLM): every reference passes its own oracle + corpus
python3 tools/run_tests.py --selftest

source config/experiment.env                 # Databricks-hosted Anthropic endpoint + token

# smoke (1+ LLM call/case): generate + validate each task once, assert correct
python3 option2/run_option2.py --check

# a run
python3 option2/run_option2.py --reps 20 --workers 8 --out-dir "$PWD/results/option2"
OUT_ROOT="$PWD/results/option1_default" WORKERS=6 bash option1/run_option1.sh 20
python3 analysis/metrics.py --results-root results
```

## Threats to validity (codegen-specific)

- **Oracle/test completeness.** A thin named suite can pass while behavior is wrong; mitigated by
  the seeded differential corpus vs the reference (correctness requires corpus agreement, not just
  named-test pass). The corpus generators may still miss some input region.
- **Undecidable equivalence.** True behavioral equivalence is undecidable; the corpus *approximates*
  it. Two genuinely different functions agreeing on all corpus inputs hash identically at the
  behavioral altitude (a possible false "same").
- **Nondeterministic candidates.** Forbidden imports + `PYTHONHASHSEED=0` reduce this; a candidate
  that is still nondeterministic could pollute its behavioral hash.
- **Sandbox is defense-in-depth, not a jail.** `rlimits` + temp `cwd` + the AST pre-check are not a
  true OS sandbox; stdlib cannot hard-block network. Tasks are pure and run locally by design.
- **Fix-loop fairness.** Both options loop, but Option 1's loop is model-driven and Option 2's is a
  fixed protocol; this biases correctness. Report behavioral consistency among *passing* runs
  separately from raw correctness.
