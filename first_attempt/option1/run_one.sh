#!/usr/bin/env bash
# One isolated Option 1 rep: a single headless `claude -p` with its own fresh
# CLAUDE_CONFIG_DIR (no inherited config/plugins/hooks/memory/MCP), scoped tools,
# inline 3P auth, no session persistence. Args: <case_id> <out_path>
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$ROOT/config/experiment.env"

CASE="$1"; OUT="$2"
mkdir -p "$(dirname "$OUT")"; rm -f "$OUT"
ISO="$(mktemp -d "${TMPDIR:-/tmp}/cc-iso-XXXXXX")"
trap 'rm -rf "$ISO"' EXIT

PROMPT="$(cat "$ROOT/option1/task_prompt.md")"
PROMPT="${PROMPT//\{\{CASE_ID\}\}/$CASE}"
PROMPT="${PROMPT//\{\{OUT_PATH\}\}/$OUT}"

ALLOWED=( "Read" "Write"
  "Bash(python3 tools/http_get.py:*)"
  "Bash(python3 tools/db_query.py:*)"
  "Bash(python3 tools/calc.py:*)"
  "Bash(python3 tools/validate_json.py:*)" )

CLAUDE_CONFIG_DIR="$ISO" \
ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL" \
ANTHROPIC_AUTH_TOKEN="$ANTHROPIC_AUTH_TOKEN" \
ANTHROPIC_MODEL="$ANTHROPIC_MODEL" \
ANTHROPIC_CUSTOM_HEADERS="$ANTHROPIC_CUSTOM_HEADERS" \
MOCK_API_PORT="${MOCK_API_PORT:-8723}" \
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

if [ -f "$OUT" ]; then
  python3 "$ROOT/tools/validate_json.py" "$OUT" >/dev/null 2>&1 \
    && echo "[$CASE] $(basename "$OUT") valid" || echo "[$CASE] $(basename "$OUT") INVALID"
else
  echo "[$CASE] $(basename "$OUT") NO-OUTPUT"
fi
