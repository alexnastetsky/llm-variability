# Output Variability: LLM-Orchestrated vs. Code-Orchestrated Pipelines

Does an LLM that *orchestrates* a multi-step task (decides the steps, calls deterministic
tools, runs a validation loop) produce more **output variability** than a deterministic program
that *drives* the steps and calls the LLM only for narrow cognitive sub-tasks?

**Finding.** Across three rounds — up to **1,000 independent Option 1 runs** on a deliberately
ambiguous, longer-horizon task — both architectures produced identical, correct graded output on
every run (consistency 1.00, entropy 0.00, correctness 1.00). The hypothesis was **not supported**:
variability comes from decision freedom / underspecification, not from LLM orchestration per se.

📄 **Full write-up: [`REPORT.md`](REPORT.md)** — setup, methodology, results, interpretation, and limitations.

## The two architectures

- **Option 1 — LLM orchestrates.** Headless Claude Code (`claude -p`) gets a prescriptive
  step-by-step prompt, deterministic tools (via Bash), Read/Write, and a validation loop, and
  drives the whole pipeline.
- **Option 2 — code orchestrates.** A Python harness runs the pipeline deterministically and calls
  the LLM (via the `anthropic` SDK against the *same* endpoint) only for the cognitive sub-steps:
  extract, classify, summary.

Both run the same model + version (`databricks-claude-opus-4-8`) via the same Databricks-hosted
Anthropic Messages API, so any difference is attributable to *who orchestrates*, not the model.
Opus 4.8 is a reasoning model with **no configurable temperature**, so both run at the model's
fixed sampling.

## Layout

```
config/experiment.env      shared endpoint/model env (fill in after auth)
data/fixtures.json         single source of truth (accounts, pricebook, sla, rules, cases)
data/inbox/*.txt           5 request inputs (ambiguous in R2/R3)
data/seed_db.py            builds data/refdb.sqlite
services/mock_api.py       local mock account REST service (run_service.sh starts it)
tools/                     shared deterministic tools: http_get, db_query, calc, validate_json
common/llm_client.py       anthropic SDK -> Databricks endpoint (Option 2)
option1/                   Claude Code runner: task_prompt.md, settings.json, run_*.sh
option2/run_option2.py     deterministic harness; LLM only for extract/classify/summary
analysis/ground_truth.py   deterministic correct answers per case
analysis/metrics.py        consistency / entropy / correctness / failure-signature report
```

## Reproduce

```bash
# one-time
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
python3 data/seed_db.py            # build the SQLite reference store
bash services/run_service.sh       # start the mock account API
databricks auth login --profile field-eng-east
#   config/experiment.env reads a fresh OAuth token from this profile when sourced.

source config/experiment.env

# smoke test (asserts correctness + same model id; prints model=claude-opus-4-8)
./.venv/bin/python option2/run_option2.py --check

# a run (example: round 3)
OUT_ROOT="$PWD/results_r3/option1_default" WORKERS=10 bash option1/run_option1.sh 200
./.venv/bin/python option2/run_option2.py --reps 20 --workers 8 --out-dir "$PWD/results_r3/option2"
./.venv/bin/python analysis/metrics.py --results-root results_r3
```

> Note: Opus 4.8 rejects a non-default `temperature` (HTTP 400), so there is no temperature flag —
> both options run at the model's fixed sampling. See `REPORT.md` §5.

## Isolation (why Option 1 runs don't taint the driving session)

Each `option1/run_one.sh` rep launches `claude -p` with a fresh `CLAUDE_CONFIG_DIR` (no inherited
config/plugins/hooks/memory/MCP), inline 3P auth (never written to `~/.claude/settings.json`),
`--setting-sources user` + explicit `--settings`, an empty `--mcp-config`, an `--allowedTools`
allowlist of only the 4 experiment tools, and `--no-session-persistence`.
