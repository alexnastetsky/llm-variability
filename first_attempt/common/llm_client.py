#!/usr/bin/env python3
"""Anthropic-SDK client pointed at the Databricks-hosted Claude endpoint.

Used by Option 2 (the deterministic harness). Option 1 uses Claude Code itself,
not this module — but both resolve to the SAME endpoint + model id.

Reads connection settings from the environment (source config/experiment.env first,
or rely on already-exported vars).
"""
import os

try:
    import anthropic
except ImportError as e:  # pragma: no cover
    raise SystemExit("The 'anthropic' package is required: pip install anthropic") from e


def _parse_custom_headers(raw):
    """ANTHROPIC_CUSTOM_HEADERS = 'Name: value' (one per line) -> dict."""
    headers = {}
    for line in (raw or "").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()
    return headers


def get_model():
    return os.environ.get("ANTHROPIC_MODEL", "databricks-claude-opus-4-8")


def get_client():
    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not base_url or "<workspace>" in base_url:
        raise SystemExit("ANTHROPIC_BASE_URL not set — source config/experiment.env after auth.")
    if not token or token.startswith("<"):
        raise SystemExit("ANTHROPIC_AUTH_TOKEN not set — source config/experiment.env after auth.")
    return anthropic.Anthropic(
        base_url=base_url,
        auth_token=token,  # sends 'Authorization: Bearer <token>'
        default_headers=_parse_custom_headers(os.environ.get("ANTHROPIC_CUSTOM_HEADERS")),
    )


def complete(client, system, user, max_tokens=1024):
    """Single-turn completion. Returns (text, model_id_reported_by_server).

    No `temperature` is sent: databricks-claude-opus-4-8 is a reasoning model and
    Anthropic removed the sampling parameters for this family (a non-default
    temperature returns HTTP 400). The model runs at its fixed sampling.
    """
    resp = client.messages.create(
        model=get_model(),
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
    return text, resp.model
