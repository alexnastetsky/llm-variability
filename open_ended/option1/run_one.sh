#!/usr/bin/env bash
# One isolated Option 1 rep for the open-ended experiment. The model writes its
# solution file(s) into a per-rep directory; AFTER it finishes, the harness runs the
# divergence oracle on that directory and writes the authoritative graded JSON.
# Args: <case_id> <out_path>
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$ROOT/config/experiment.env"

CASE="$1"; OUT="$2"
SPEC_PATH="$ROOT/data/specs/$CASE.md"
SOLUTION_DIR="${OUT%.json}.solution"
mkdir -p "$(dirname "$OUT")"; rm -f "$OUT"; rm -rf "$SOLUTION_DIR"; mkdir -p "$SOLUTION_DIR"
ISO="$(mktemp -d "${TMPDIR:-/tmp}/cc-iso-XXXXXX")"
trap 'rm -rf "$ISO"' EXIT

PROMPT="$(cat "$ROOT/option1/task_prompt.md")"
PROMPT="${PROMPT//\{\{CASE_ID\}\}/$CASE}"
PROMPT="${PROMPT//\{\{SPEC_PATH\}\}/$SPEC_PATH}"
PROMPT="${PROMPT//\{\{SOLUTION_DIR\}\}/$SOLUTION_DIR}"

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

python3 "$ROOT/tools/record_run.py" "$CASE" "$SOLUTION_DIR" "$OUT" --model "$ANTHROPIC_MODEL"
