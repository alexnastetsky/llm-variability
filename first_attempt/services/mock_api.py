#!/usr/bin/env python3
"""Local mock REST service — the experiment's deterministic "third-party" account API.

GET /account/<id>  -> {"account_id", "tier", "region"}   (200) or {"error"} (404)
GET /health        -> {"status": "ok"}

Responses are fixed (sourced from data/fixtures.json), so the service access step
is fully deterministic. Stdlib only — no Flask.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "..", "data", "fixtures.json")
PORT = int(os.environ.get("MOCK_API_PORT", "8723"))

with open(FIXTURES) as f:
    ACCOUNTS = json.load(f)["accounts"]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parts = [p for p in self.path.split("?")[0].strip("/").split("/") if p]
        if parts == ["health"]:
            return self._send(200, {"status": "ok"})
        if len(parts) == 2 and parts[0] == "account":
            acct = ACCOUNTS.get(parts[1])
            if acct is None:
                return self._send(404, {"error": f"unknown account {parts[1]}"})
            return self._send(200, {"account_id": parts[1], "tier": acct["tier"], "region": acct["region"]})
        return self._send(404, {"error": "not found"})

    def log_message(self, *args):
        pass  # quiet


if __name__ == "__main__":
    print(f"mock_api listening on http://127.0.0.1:{PORT}  (GET /account/<id>, /health)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
