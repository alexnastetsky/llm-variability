# LLM Output Variability: who orchestrates matters?

A pair of experiments probing one question:

> Does an LLM that **orchestrates** a multi-step task (decides the steps, calls deterministic
> tools, runs a validation loop) produce more **output variability** than a deterministic program
> that **drives** the steps and calls the LLM only for narrow sub-tasks?

Both experiments hold the model and endpoint fixed (`databricks-claude-opus-4-8` via the
Databricks-hosted Anthropic Messages API, fixed sampling — Opus 4.8 has no configurable
temperature) and compare two architectures on the same workload:

- **Option 1 — LLM orchestrates:** headless Claude Code (`claude -p`) with a prescriptive prompt,
  deterministic tools, and a validation loop, run in strict isolation.
- **Option 2 — code orchestrates:** a Python harness drives the pipeline deterministically and
  calls the LLM only for the cognitive sub-step(s).

So any difference in output dispersion is attributable to *who orchestrates*, not the model.

## Experiments

### [`first_attempt/`](first_attempt/) — customer-triage pipeline
A fully-specified, structured-output pipeline (file I/O → extract → service lookup → DB query →
arithmetic → branch → write). The graded output is a fixed schema of structured fields.
**Finding:** across up to 1,000 runs, both architectures were perfectly consistent (consistency
1.00, entropy 0.00, correctness 1.00) — the hypothesis was *not* supported. Variability came from
*decision freedom / underspecification*, not from LLM orchestration per se. See
[`first_attempt/REPORT.md`](first_attempt/REPORT.md).

One field the triage experiment *couldn't* grade was the free-text `summary` (no deterministic
ground truth) — and it varied on nearly every run. That observation motivates the second
experiment.

### [`codegen/`](codegen/) — code generation + validation
The workload is generating a small Python function and validating it by **execution**. Generated
code is prose-like on the surface (it varies run-to-run) **but**, unlike prose, it has a
*behavioral* oracle: compile it and run it against tests + a seeded differential-testing corpus.
So we grade a free-form artifact by its **observable behavior**, and measure variability at three
altitudes — **text** (raw source), **structural** (AST-normalized), and **behavioral** (test +
corpus result vector, the primary metric). Code generation also restores real decision freedom,
making it the sharper test of the hypothesis.

**Finding:** across 200 runs (10 tasks — 5 trivial + 5 hard — × K=10 × both architectures, under 3
prompt variants each), behavioral consistency and correctness were **1.00** for both architectures.
Source text varied on nearly every run (text consistency down to 0.10 on the hard tasks), yet
behavior never diverged — complexity raised *textual* variability but not *behavioral* variability.
The hypothesis was again **not supported**. See [`codegen/README.md`](codegen/README.md) and
[`codegen/REPORT.md`](codegen/REPORT.md).

### [`open_ended/`](open_ended/) — underspecified + multi-file tasks
Both prior experiments used **fully-specified** tasks and found zero behavioral variability, with a
shared conclusion: variability comes from *decision freedom*, not orchestration. This experiment
tests that directly by **removing the specification** — tasks that admit many correct behaviors
(unspecified tie-breaks, rounding modes, output order/schema) plus multi-file tasks. Grading flips
from "match the reference" to **"do runs converge or diverge?"** (count distinct behavioral
fingerprints among contract-valid runs).

**Finding:** divergence finally appears — and **only** here (the fully-specified control and the two
prior experiments show none). At K=20 over 11 tasks (440 runs, all valid), divergence showed up on 6
tasks, and **Option 1 (Claude Code) diverged on more axes than Option 2 — 5 tasks vs 2** — the
strongest support yet for the original hypothesis (e.g. it split between banker's and half-up
rounding where Option 2 stayed consistent). The divergence is in conventions/representation (rounding
mode, numeric type, output schema, truthy vocabulary), not correctness, and splits are usually
lopsided (a strong default deviated from occasionally). It's a tendency, not a law — one task
diverged only under Option 2. See [`open_ended/README.md`](open_ended/README.md) and
[`open_ended/REPORT.md`](open_ended/REPORT.md).

### The arc
Fully-specified structured pipeline (`first_attempt`) → fully-specified code generation, incl. hard
tasks (`codegen`) → **underspecified + multi-file** (`open_ended`). Variability stays at zero until
the spec leaves room; then it appears, and LLM orchestration produces more of it than code
orchestration. Underspecification — not LLM orchestration alone — is the driver, and orchestration
amplifies it.

## Shared design

Each experiment is **self-contained** (its own `config/`, `common/`, tools, runners, analysis) so
it can be run independently. Both reuse the same harness shape:
`option1/` (Claude Code runner with isolation), `option2/run_option2.py` (deterministic harness),
and `analysis/metrics.py` (consistency / normalized entropy / correctness / failure signatures —
the math is workload-agnostic; only the per-run *grading identity* differs).

```
first_attempt/   the triage-pipeline experiment (fully specified)
codegen/         the code-generation experiment (fully specified, incl. hard tasks)
open_ended/      underspecified + multi-file tasks (where divergence appears)
requirements.txt single dependency: anthropic
```

Dependencies: `pip install -r requirements.txt` (just `anthropic`; everything else is stdlib).
