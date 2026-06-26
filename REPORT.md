# Output Variability: LLM-Orchestrated vs. Code-Orchestrated Pipelines

**Question.** Does an LLM that *orchestrates* a multi-step task (deciding the steps, calling
deterministic tools, running a validation loop) produce more **output variability** than a
deterministic program that *drives* the steps and calls the LLM only for narrow sub-tasks?

**Hypothesis (going in).** Option 1 (LLM-orchestrated) would show more output variability than
Option 2 (code-orchestrated), with most of the divergence appearing at **step hand-offs** — where
the orchestrator passes one step's result to the next, or skips a step.

**Finding (headline).** Across three rounds — culminating in **1,000 independent Option 1 runs** on
a deliberately ambiguous, longer-horizon task — **both architectures produced identical, correct
graded output on every run** (consistency 1.00, entropy 0.00, correctness 1.00). The hypothesis was
**not supported** under the conditions tested. Output variability appears to come from *decision
freedom / underspecification*, not from LLM orchestration per se; a fully-specified task removes it.

---

## 1. Setup

### Model & endpoint
- **Model:** `databricks-claude-opus-4-8` (the server reports it as `claude-opus-4-8` — the same
  version Claude Code uses natively), so **both options use the identical model + version by
  construction**.
- **Endpoint:** Databricks-hosted **native Anthropic Messages API**
  (`https://adb-984752964297111.11.azuredatabricks.net/serving-endpoints/anthropic`), profile
  `field-eng-east`. No LiteLLM / proxy — Claude Code and the `anthropic` SDK both speak to it
  directly (auth via `ANTHROPIC_AUTH_TOKEN` + `x-databricks-use-coding-agent-mode` header).
- **Temperature:** **not configurable.** Opus 4.8 is a reasoning model; Anthropic removed
  `temperature`/`top_p`/`top_k` for this family (a non-default value returns HTTP 400). Both options
  therefore run at the model's fixed sampling. The originally-planned temp 0.0 / 1.0 decomposition
  was dropped for this reason (confirmed against the Claude API docs and the live endpoint).

### The two architectures
- **Option 1 — LLM orchestrates.** Headless Claude Code (`claude -p`) is given a prescriptive
  step-by-step prompt (`option1/task_prompt.md`), deterministic tools (invoked via Bash), the
  Read/Write tools, and a validation loop. The agent drives the whole pipeline.
- **Option 2 — code orchestrates.** A Python harness (`option2/run_option2.py`) executes the
  pipeline deterministically and calls the LLM (via the `anthropic` SDK against the *same* endpoint)
  only for the cognitive sub-steps: **extract**, **classify**, **summary**. File I/O, service
  lookup, DB query, arithmetic, discounts, and the branch are pure Python (zero variance).

### Workload — a customer-request triage pipeline
Each case is an email-style request; the pipeline produces a structured quote + routing record.
The task crosses **modality boundaries** (where hand-offs are most likely to break): file I/O →
NL extraction → third-party service call → data-store query → arithmetic → conditional branch →
file I/O.

- **Deterministic resources** (single source of truth: `data/fixtures.json`):
  - a **local mock REST service** (`services/mock_api.py`) — the "third-party" account API
    (`GET /account/<id>` → tier, region), fixed responses;
  - a **SQLite reference store** (`data/refdb.sqlite`) — pricebook + SLA tables;
  - 5 **request files** (`data/inbox/case0{1..5}.txt`).
- **Shared tools** (`tools/`), used by *both* options so I/O and arithmetic errors can't masquerade
  as orchestration variability: `http_get`, `db_query`, `calc`, `validate_json`.

### Metrics (`analysis/metrics.py`)
Per condition × case, over K repeated runs:
- **consistency rate** — fraction of runs equal to the modal output (1.00 = identical every time);
- **distinct outputs** and **normalized entropy** (0.00 = no variability);
- **correctness** — fraction matching deterministic ground truth (`analysis/ground_truth.py`);
- **failure-signature breakdown** — classifies any wrong output (e.g. dropped long-range hand-off).

The graded "output" is the tuple of structured fields (floats rounded to 2 dp). The free-text
`summary` is **excluded** from grading. Missing/errored runs are tracked separately.

### Isolation (Option 1 runs can't contaminate the driving session)
Both the driver and every Option 1 rep are Claude Code, so each rep is launched with: a **fresh
`CLAUDE_CONFIG_DIR`** (no inherited config/plugins/hooks/memory/MCP), **inline 3P-auth env** (never
written to `~/.claude/settings.json`), `--setting-sources user`, explicit `--settings`, an empty
`--mcp-config`, an `--allowedTools` allowlist of only the 4 experiment tools, and
`--no-session-persistence`. Verified: the driver's `~/.claude` was untouched.

---

## 2. Methodology notes that matter

- **The validator is ground-truth-free *on purpose*.** `tools/validate_json.py` checks only
  (a) structure/enums and (b) internal arithmetic consistency (`subtotal = price×qty`,
  `total = subtotal × discounts`). It does **not** know the correct account, quantity, tier,
  category, or decision. We proved a deliberately *wrong* answer (shipping-account decoy,
  upper-bound quantity, wrong tier/category, decision contradicting its own tier) passes as `VALID`.
  → The validation loop does **not** force correctness; divergence *could* surface and exit the loop.
  The only variability channel it removes is arithmetic typos — already near-zero because math is
  offloaded to the `calc` tool.
- **Runs are genuinely independent.** The ungraded `summary` field varied across reps (e.g. 18 of 20
  distinct for one case) while the graded fields were identical — confirming the perfect consistency
  is real model behavior, not duplicate files or caching.
- **Same model id asserted at runtime** in both paths (`claude-opus-4-8`), satisfying the
  "same model + version" requirement.

---

## 3. Experiment rounds & results

| Round | Task | Option 1 | Option 2 | Result (both conditions) |
|---|---|---|---|---|
| **R1** | Well-specified 7-step pipeline | K=5 | K=5 @ fixed sampling | consistency **1.00**, entropy **0.00**, correct **1.00** |
| **R2** | **Ambiguous + longer-horizon** (range qty, billing-vs-shipping decoy, red herrings, stacking volume+tier discounts, escalation on *post-discount* total) | K=20 | K=20 | consistency **1.00**, entropy **0.00**, correct **1.00** |
| **R3** | Same R2 task | **K=200 (1,000 runs)** | K=20 (reused) | consistency **1.00**, entropy **0.00**, correct **1.00** |

**Round 2/3 ambiguity, concretely** — each was navigated identically on every run:
- *Account selection:* "bill to ACC-1001, ship to ACC-1004" → always chose the billing account.
- *Quantity interpretation:* "between 20 and 25" → 20; "a dozen" → 12; "two dozen" → 24; unstated → 1.
- *Long-range dependency:* the escalation decision depends on the **post-discount** total, computed
  from account→tier→discounts established several steps earlier.
- *Red herrings:* "our enterprise plan" (tier came from the service lookup, not the wording);
  "please ESCALATE!" (narrative, not the business rule).

**Infra note (R3):** at 10-way concurrency, ~39/1000 runs returned `API Error: Connection closed
mid-response` (the endpoint dropping connections under load) and wrote no file. These are **infra
failures, not divergence**; they were excluded from the consistency numbers and then **re-run at
3-way concurrency**, all 39 succeeding → a clean **1,000/1,000 valid**.

---

## 4. Interpretation

1. **The hypothesis was not supported — with statistical weight.** With 200 reps/case and zero
   divergences, the rule-of-three gives a 95% upper bound on the true per-run divergence rate of
   roughly **<1.5%** on this task. Whatever orchestration variability exists here is rarer than that.
2. **Output variability is not inherent to LLM orchestration.** On a fully-specified task
   (prescriptive recipe + deterministic tools + validation loop) with a fixed-sampling reasoning
   model, the LLM-orchestrated path was **exactly as deterministic as code orchestration**.
3. **The driver of variability is decision freedom / underspecification, not orchestration itself.**
   The prescriptive prompt spells out how to resolve every ambiguity, so the LLM executes a recipe
   rather than making free hand-off decisions — and the messy input no longer matters.

---

## 5. Limitations / threats to validity

- **One task family, one model** (`databricks-claude-opus-4-8`).
- **Recipe-style Option 1 prompt held constant.** The single most likely lever to *produce*
  divergence — a **de-scaffolded, goal-only prompt** that returns hand-off decisions to the LLM —
  was deliberately not varied. That is the natural next experiment to find where variability emerges.
- **No temperature axis.** Opus 4.8 has no configurable sampling, so a temp-0 "determinism floor"
  decomposition wasn't possible; both options run at the model's fixed sampling.
- **Option 2 at K=20** (vs Option 1 at K=200). Both were flat; raising Option 2's K is cheap if a
  tighter bound is wanted.
- **Graded fields only.** Free-text output (the `summary`) *did* vary every run — variability lives
  in the ungoverned part of the output, which is expected and not what the hypothesis was about.

---

## 6. Reproduce

```bash
# one-time
python3 data/seed_db.py            # build SQLite reference store
bash services/run_service.sh       # start the mock account API
databricks auth login --profile field-eng-east
#   set ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN in config/experiment.env  (see README)

source config/experiment.env

# smoke tests (assert correctness + same model id)
./.venv/bin/python option2/run_option2.py --check          # 5 cases, prints model=claude-opus-4-8

# a run (example: round 3)
OUT_ROOT="$PWD/results_r3/option1_default" WORKERS=10 bash option1/run_option1.sh 200
./.venv/bin/python option2/run_option2.py --reps 20 --workers 8 --out-dir "$PWD/results_r3/option2"
./.venv/bin/python analysis/metrics.py --results-root results_r3
```

### File map
```
config/experiment.env       endpoint/model env (both runners source this)
data/fixtures.json          single source of truth (accounts, pricebook, sla, rules, cases)
data/inbox/*.txt            5 request inputs (ambiguous in R2/R3)
data/seed_db.py             builds data/refdb.sqlite
services/mock_api.py        local mock account REST service
tools/                      http_get, db_query, calc, validate_json (shared, ground-truth-free)
common/llm_client.py        anthropic SDK -> Databricks endpoint (Option 2)
option1/task_prompt.md      Option 1 prescriptive prompt (step-by-step recipe)
option1/run_one.sh          one isolated `claude -p` rep
option1/run_option1.sh      Option 1 driver (fans out across a worker pool)
option2/run_option2.py      deterministic harness; LLM only for extract/classify/summary
analysis/ground_truth.py    deterministic correct answers per case
analysis/metrics.py         consistency / entropy / correctness / failure signatures
results_r2/, results_r3/    raw run outputs per round
```
