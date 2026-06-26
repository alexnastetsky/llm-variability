#!/usr/bin/env bash
# One isolated Option 1 rep: a single headless `claude -p` that generates + validates a
# solution, run with its own fresh CLAUDE_CONFIG_DIR (no inherited config/plugins/hooks/
# memory/MCP), scoped tools, inline 3P auth, no session persistence. Args: <case_id> <out_path>
#
# The MODEL writes only the solution .py (via the validation loop); AFTER it finishes, the
# harness itself runs the oracle and writes the authoritative graded JSON to <out_path>.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$ROOT/config/experiment.env"

CASE="$1"; OUT="$2"
SOLUTION="${OUT%.json}.solution.py"
mkdir -p "$(dirname "$OUT")"; rm -f "$OUT" "$SOLUTION"
ISO="$(mktemp -d "${TMPDIR:-/tmp}/cc-iso-XXXXXX")"
trap 'rm -rf "$ISO"' EXIT

PROMPT="$(cat "$ROOT/option1/task_prompt.md")"
PROMPT="${PROMPT//\{\{CASE_ID\}\}/$CASE}"
PROMPT="${PROMPT//\{\{SOLUTION_PATH\}\}/$SOLUTION}"

ALLOWED=( "Read" "Write" "Bash(python3 tools/run_tests.py:*)" )

CLAUDE_CONFIG_DIR="$ISO" \
ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL" \
ANTHROPIC_AUTH_TOKEN="$ANTHROPIC_AUTH_TOKEN" \
ANTHROPIC_MODEL="$ANTHROPIC_MODEL" \
ANTHROPIC_CUSTOM_HEADERS="$ANTHROPIC_CUSTOM_HEADERS" \
claude -p "$PROMPT" \
  --model "$ANTHROPIC_MODEL" \
  --setting-sources user \
  --settings "$ROOT/option1/settings.json" \
  --mcp-config "$ROOT/option1/mcp-empty.json" \
  --add-dir "$ROOT" \
  --allowedTools "${ALLOWED[@]}" \
  --permission-mode default \
  --no-session-persistence \
  --output-format text \
  >"${OUT%.json}.log" 2>&1

# Harness-authoritative grading: run the oracle on the model's final solution.
python3 "$ROOT/tools/record_run.py" "$CASE" "$SOLUTION" "$OUT" --model "$ANTHROPIC_MODEL"
