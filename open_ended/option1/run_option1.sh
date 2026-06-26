#!/usr/bin/env bash
# Option 1 driver for the open-ended experiment — fans out isolated reps.
#   Usage:  bash option1/run_option1.sh [REPS] [CASE...]
#   Env:    OUT_ROOT (default results/option1_default), WORKERS (default 5)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$ROOT/config/experiment.env"

REPS="${1:-10}"; shift || true
CASES=("$@")
if [ ${#CASES[@]} -eq 0 ]; then
  CASES=()
  for c in $(python3 -c 'import json;print(" ".join(json.load(open("data/cases.json"))))'); do
    CASES+=("$c")
  done
fi
OUT_ROOT="${OUT_ROOT:-$ROOT/results/option1_default}"
WORKERS="${WORKERS:-5}"

echo "Option 1: ${#CASES[@]} cases x $REPS reps, $WORKERS workers -> $OUT_ROOT"
for c in "${CASES[@]}"; do
  for i in $(seq 0 $((REPS - 1))); do
    printf -v r "run_%03d.json" "$i"
    printf '%s\t%s\n' "$c" "$OUT_ROOT/$c/$r"
  done
done | xargs -P "$WORKERS" -L1 bash -c 'bash "$0/option1/run_one.sh" "$1" "$2"' "$ROOT"

echo "Option 1 done -> $OUT_ROOT"
