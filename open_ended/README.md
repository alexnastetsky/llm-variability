# Open-Ended Tasks: underspecified + multi-file code generation

The third experiment in this repo (see the [top-level README](../README.md)). Same hypothesis —
does an LLM that **orchestrates** produce more output variability than deterministic code that
**drives** and calls the LLM only to generate? — but the workload is deliberately built to let
variability appear: **underspecified** tasks (many correct behaviors) and **multi-file** tasks.

📄 **Results: [`REPORT.md`](REPORT.md).** This is the experiment where divergence shows up. At K=30
over 18 tasks (1080 runs, all valid), divergence appeared on 6 underspecified tasks; **Option 1
(Claude Code) diverged on more axes than Option 2 — 5 vs 4** — and was **~7× slower per run**. Both
controls converged at 1@1.00. The divergence is in conventions/representation (rounding mode,
numeric type, output schema, capitalization, acronym splitting), not correctness; splits are usually
lopsided. `analysis/divergence.py` auto-documents the diverging axis + split per task.

## Task naming

`u##` = **underspecified** task (the variable under study). `ctl##` = **control** (fully specified,
one correct behavior). Multi-file tasks are flagged by a `multifile` field in `data/cases.json`, not
by the name. (The prefix encodes the task's *role*, not its file count.)

## Why this workload

The first two experiments used fully-specified tasks and found zero behavioral variability. The
natural next step (flagged in their limitations) is to remove the specification. Here the tasks
admit multiple correct behaviors, so we can ask whether runs **converge or diverge** on the free
choices — and whether LLM orchestration diverges more than code orchestration.

## Grading: divergence, not correctness

There is no single correct answer, so grading flips:
- **validity** — does the candidate satisfy a permissive per-task **contract** (`data/contracts/`)
  on every seeded corpus input? (the "acceptable behavior" checker, replacing "correctness").
- **behavioral fingerprint** — a hash of the candidate's output vector over the fixed corpus. Same
  fingerprint = same behavior; **different fingerprints across runs = divergence**. The headline
  metric is the count of distinct fingerprints among valid runs.

## The 18 tasks

- **Underspecified, numeric/structural (`u1`–`u9`):** `rank_items` (tie order), `round_all`
  (half-rounding), `top_k` (output order), `dedup` (order/which occurrence), `argmax` (tie index),
  `median_of` (even-length convention), `most_common` (mode tie), `top_k_indices` (indices on ties),
  `parse_bool` (truthy vocabulary).
- **Underspecified, multi-file (`u10_stats`):** `core.py` + `api.py` exposing `summary(nums)` (key
  names, median convention, numeric types all free).
- **Underspecified, text (`u11`–`u16`):** `titlecase` (which words capitalized), `slugify`
  (separator/punctuation), `initials` (formatting), `camel_to_snake` (acronym-run splitting),
  `normalize_whitespace` (trim/collapse), `strip_punctuation` (which punctuation removed).
- **Controls (`ctl1_roman` multi-file, `ctl2_reverse` text):** fully specified, one correct behavior
  — the convergence baseline (and a check that multi-file structure alone doesn't cause divergence).

Each task's intended axis is recorded in `data/cases.json`. A candidate solution is a **directory**
of one or more `.py` files; the oracle imports the entry module (multi-file solutions use absolute
imports like `from core import ...`).

## Layout

```
data/cases.json            registry: func_name, entry, kind, control, multifile, files, axis, corpus_seed
data/specs/<case>.md       spec shown to the model (deliberately leaves choices open)
data/contracts/<case>.py   check(args, output) -> bool: is this output ACCEPTABLE?
data/reference/<case>/      one valid reference solution (single file or core.py+api.py); selftest only
tools/corpus.py            seeded inputs biased toward ties/halves/duplicates/even-lengths
tools/_runner.py           subprocess: add solution dir to path, import entry module, call func
tools/run_tests.py         divergence oracle: validity + behavioral fingerprint; --selftest
tools/record_run.py        build the graded run JSON from a solution directory
option1/                   Claude Code runner (writes a solution dir): task_prompt.md, run_*.sh
option2/run_option2.py     deterministic harness; multi-file response parsing; bounded fix loop
analysis/metrics.py        distinct behaviors / behavioral consistency / validity per condition x case
analysis/divergence.py     auto-characterizes the diverging axis + split (with examples) per task
config/, common/           copied from codegen (self-contained)
```

## Reproduce

```bash
pip install -r ../requirements.txt
python3 tools/run_tests.py --selftest
source config/experiment.env
python3 option2/run_option2.py --check

python3 option2/run_option2.py --reps 30 --workers 8 --out-dir "$PWD/results_full/option2"
OUT_ROOT="$PWD/results_full/option1_default" WORKERS=6 bash option1/run_option1.sh 30
python3 analysis/metrics.py    --results-root results_full
python3 analysis/divergence.py --results-root results_full   # diverging axis + split per task
```
