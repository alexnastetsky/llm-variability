# Open-Ended Tasks: underspecified + multi-file code generation

The third experiment in this repo (see the [top-level README](../README.md)). Same hypothesis —
does an LLM that **orchestrates** produce more output variability than deterministic code that
**drives** and calls the LLM only to generate? — but the workload is deliberately built to let
variability appear: **underspecified** tasks (many correct behaviors) and **multi-file** tasks.

📄 **Results: [`REPORT.md`](REPORT.md).** This is the experiment where divergence finally shows up.
At K=20 over 11 tasks (440 runs, all valid), divergence appeared on 6 tasks, and **Option 1 (Claude
Code) diverged on more axes than Option 2 — 5 tasks vs 2** — the strongest support yet for the
original hypothesis. The divergence is in conventions/representation (rounding mode, numeric type,
output schema, truthy vocabulary), not correctness; splits are usually lopsided (a strong default
deviated from occasionally). `analysis/divergence.py` auto-documents the diverging axis + split per
task.

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

## The 11 tasks

- **9 underspecified single-file tasks**, each isolating one ambiguity axis: `rank_items` (tie
  order), `round_all` (half-rounding), `top_k` (output order), `dedup` (order/which occurrence),
  `argmax` (tie index), `median_of` (even-length convention), `most_common` (mode tie),
  `top_k_indices` (indices on ties), `parse_bool` (truthy vocabulary). Each task's intended axis is
  recorded in `data/cases.json`.
- **Multi-file, underspecified:** `m1_stats` — `core.py` + `api.py` exposing `summary(nums)` (key
  names, median convention, numeric types all free).
- **Multi-file, fully-specified control:** `m2_roman` — `core.py` + `api.py` exposing `to_roman(n)`;
  one correct behavior (tests whether multi-file structure alone causes divergence — it doesn't).

A candidate solution is a **directory** of one or more `.py` files; the oracle imports the entry
module (`data/cases.json` gives the entry module + function; multi-file solutions use absolute
imports like `from core import ...`).

## Layout

```
data/cases.json            registry: func_name, entry module, mode, files, corpus_seed
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

python3 option2/run_option2.py --reps 20 --workers 8 --out-dir "$PWD/results_full/option2"
OUT_ROOT="$PWD/results_full/option1_default" WORKERS=5 bash option1/run_option1.sh 20
python3 analysis/metrics.py    --results-root results_full
python3 analysis/divergence.py --results-root results_full   # diverging axis + split per task
```
