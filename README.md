# Output-Variability Experiment: LLM-orchestrated vs. Code-orchestrated

Tests the hypothesis that **Option 1** (an LLM — Claude Code — with skills orchestrates
deterministic tools + a validation loop) produces more **output variability** than **Option 2**
(deterministic code drives the steps and calls the LLM only for cognitive sub-tasks).

Both options run the **same 7-step pipeline** on the **same model + version**
(`databricks-claude-opus-4-8`) via the **same Databricks-hosted Anthropic endpoint**, so any
difference in output dispersion is attributable to *who orchestrates*, not the model.

## The workload (mixed modalities)

A customer-request triage pipeline whose steps cross modality boundaries (where hand-offs break):

1. **Read input** (file I/O) — `data/inbox/<case>.txt`
2. **Extract** (cognitive) — account_id, product, quantity
3. **Service lookup** (third-party) — `GET /account/<id>` on the local mock API → tier
4. **Reference query** (data store) — SQLite pricebook + SLA
5. **Compute** (arithmetic) — `total = unit_price * quantity`
6. **Branch** (rules) — `ESCALATE` iff `tier==Enterprise AND total>10000` (long-range tier hand-off)
7. **Write output** (file I/O) — final JSON

In **Option 2**, steps 1/3/4/5/6 are pure code (zero variance); the LLM is called only for
extract/classify/summary. In **Option 1**, Claude Code drives everything.

## Layout

```
config/experiment.env      shared endpoint/model env (FILL IN after auth)
data/fixtures.json         single source of truth (accounts, pricebook, sla, rules, cases)
data/inbox/*.txt           5 request inputs
data/seed_db.py            builds data/refdb.sqlite
services/mock_api.py       local mock account API (stdlib); run_service.sh starts it
tools/                     shared deterministic tools: http_get, db_query, calc, validate_json
common/llm_client.py       anthropic SDK -> Databricks endpoint (Option 2 only)
option1/                   Claude Code runner: task_prompt.md, settings.json, run_option1.sh
option2/run_option2.py     deterministic harness (--temperature flag)
analysis/ground_truth.py   deterministic correct answers per case
analysis/metrics.py        consistency / entropy / correctness / failure-signature report
.venv/                     python deps (anthropic, numpy)
```

## Setup (one-time)

```bash
# 0. Python deps already installed in .venv (anthropic, numpy).
# 1. Seed the reference DB and start the mock service.
python3 data/seed_db.py
bash services/run_service.sh

# 2. Authenticate to Databricks and fill in config/experiment.env  (OPEN ITEM 1)
databricks auth login --profile <profile>
#    Set ANTHROPIC_BASE_URL to https://<workspace>.cloud.databricks.com/serving-endpoints/anthropic
#    (or .../ai-gateway/anthropic), and export a token:
#    export ANTHROPIC_AUTH_TOKEN="$(databricks auth token -p <profile> | jq -r .access_token)"
```

## Smoke tests (do before the pilot)

```bash
source config/experiment.env
# Endpoint + version assertion (Option 2 path):
./.venv/bin/python option2/run_option2.py --check          # asserts correctness @ temp 0, prints model id
# Claude Code routes to Databricks + isolation holds (Option 1 path):
bash option1/run_option1.sh 1 case01                       # one isolated rep; check it wrote a valid file
```

If `--check` prints `model=databricks-claude-opus-4-8` and Option 1's log shows the same model, the
"same model + version" requirement is proven.

## Run the pilot (3 conditions, K=20 × 5 cases)

```bash
source config/experiment.env
bash   option1/run_option1.sh 20                           # Option 1 (CC default temp)
./.venv/bin/python option2/run_option2.py --temperature 1.0 --reps 20
./.venv/bin/python option2/run_option2.py --temperature 0.0 --reps 20
./.venv/bin/python analysis/metrics.py                     # comparison table
```

**Expected if the hypothesis holds:** Option 2 @ 0.0 ≈ floor (consistency ~1.0, entropy ~0);
Option 1 shows lower consistency / higher entropy than Option 2 @ 1.0, and more hand-off failure
signatures (notably `decision_inconsistent_with_own_fields` and `wrong_tier`).

## Isolation (why Option 1 runs don't taint this session)

Each `option1/run_option1.sh` rep launches `claude -p` with a fresh `CLAUDE_CONFIG_DIR` (no
inherited user config/plugins/hooks/memory/MCP), inline 3P-auth env (never written to
`~/.claude/settings.json`), `--setting-sources user` + explicit `--settings`, an empty
`--mcp-config`, an `--allowedTools` allowlist of only the 4 experiment tools, and
`--no-session-persistence`. See the plan for the full rationale.

## Known limitation

Claude Code does not expose a temperature setting, so Option 1 runs at CC's fixed default. Option 2
is run at both 1.0 (sampling-matched) and 0.0 (determinism floor) to bracket it.
