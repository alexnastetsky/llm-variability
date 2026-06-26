#!/usr/bin/env bash
# Start the mock account API in the background and write its PID to services/mock_api.pid.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${MOCK_API_PORT:-8723}"

python3 "$HERE/mock_api.py" >"$HERE/mock_api.log" 2>&1 &
echo $! >"$HERE/mock_api.pid"
sleep 1
if curl -fs "http://127.0.0.1:${PORT}/health" >/dev/null; then
  echo "mock_api started (pid $(cat "$HERE/mock_api.pid"), port ${PORT})"
else
  echo "mock_api failed to start; see $HERE/mock_api.log" >&2
  exit 1
fi
