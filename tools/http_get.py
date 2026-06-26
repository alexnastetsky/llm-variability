#!/usr/bin/env python3
"""Deterministic HTTP GET against the local mock account service.

CLI:    python3 tools/http_get.py /account/ACC-1001
Import: from tools.http_get import http_get; http_get("/account/ACC-1001")
"""
import json
import os
import sys
import urllib.request

PORT = os.environ.get("MOCK_API_PORT", "8723")
BASE = f"http://127.0.0.1:{PORT}"


def http_get(path: str):
    """GET <base><path> and return parsed JSON. Raises on non-200."""
    if not path.startswith("/"):
        path = "/" + path
    with urllib.request.urlopen(BASE + path, timeout=10) as resp:
        return json.loads(resp.read().decode())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: http_get.py /account/<id>", file=sys.stderr)
        sys.exit(2)
    try:
        print(json.dumps(http_get(sys.argv[1])))
    except urllib.error.HTTPError as e:
        print(e.read().decode(), file=sys.stderr)
        sys.exit(1)
