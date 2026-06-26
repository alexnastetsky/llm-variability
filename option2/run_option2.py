#!/usr/bin/env python3
"""Option 2 — DETERMINISTIC code orchestrates the 7-step pipeline and calls the
LLM only for the cognitive sub-steps (extract, classify, summary).

Code owns every hand-off: file I/O, the service lookup, the DB query, the
arithmetic, and the branch are pure Python (zero variance). The LLM surface is
deliberately small and tightly scoped, so output variability should be low.

No temperature axis: databricks-claude-opus-4-8 is a reasoning model with fixed
sampling (Anthropic removed temperature/top_p/top_k for this family). Both
options run at the model's default sampling.

Usage:
  python3 option2/run_option2.py --reps 20
  python3 option2/run_option2.py --reps 20 --cases case01
  python3 option2/run_option2.py --check          # one rep/case, assert correctness
"""
import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from tools.http_get import http_get          # noqa: E402
from tools.db_query import query_price, query_sla  # noqa: E402
from tools.validate_json import validate      # noqa: E402
from analysis.ground_truth import ground_truth, GRADEABLE_FIELDS  # noqa: E402
from common.llm_client import get_client, complete, get_model  # noqa: E402

INBOX = os.path.join(ROOT, "data", "inbox")
with open(os.path.join(ROOT, "data", "fixtures.json")) as f:
    FX = json.load(f)
THRESHOLD = FX["rules"]["escalation_threshold"]
DEFAULT_QTY = 1  # rule: if no quantity is stated, assume 1
CATEGORIES = FX["categories"]


def _extract_json(text):
    """Pull the first JSON object out of an LLM response (tolerates code fences)."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start = text.find("{")
    if start == -1:
        raise ValueError(f"no JSON object in response: {text!r}")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError(f"unbalanced JSON in response: {text!r}")


# ---- cognitive sub-steps (the ONLY LLM calls) ----

def llm_extract(client, request_text):
    sys_p = ("You extract structured fields from a customer request. "
             "Respond with ONLY a JSON object, no prose.")
    user_p = (
        "Extract these fields from the request:\n"
        '  - account_id (string like "ACC-1234"). If more than one account is mentioned, use the\n'
        "    account being billed / placing the order, NOT a shipping, parent, or referenced account.\n"
        "  - product (the product code mentioned)\n"
        "  - quantity (integer). Interpret natural language ('a dozen'=12, 'two dozen'=24);\n"
        "    for a range use the lower bound; if no quantity is stated, use 1.\n\n"
        f"REQUEST:\n{request_text}\n\n"
        'Return exactly: {"account_id": ..., "product": ..., "quantity": ...}'
    )
    text, model = complete(client, sys_p, user_p, max_tokens=200)
    return _extract_json(text), model


def llm_classify(client, request_text):
    sys_p = "You classify a customer request into exactly one category."
    user_p = (
        f"Categories: {', '.join(CATEGORIES)}.\n"
        f"REQUEST:\n{request_text}\n\n"
        "Reply with ONLY the single category word."
    )
    text, model = complete(client, sys_p, user_p, max_tokens=20)
    label = text.strip().strip(".").lower()
    return label, model


def llm_summary(client, fields):
    sys_p = "You write a one-sentence internal summary of a triaged request."
    user_p = ("Write a single concise sentence summarizing this triaged request "
              f"(do not add new facts):\n{json.dumps(fields)}")
    text, _ = complete(client, sys_p, user_p, max_tokens=120)
    return text.strip()


# ---- deterministic orchestration ----

def run_pipeline(client, case_id):
    # Step 1 — file I/O (code)
    with open(os.path.join(INBOX, f"{case_id}.txt")) as fh:
        request_text = fh.read()

    # Step 2 — extract (LLM)
    extracted, model_id = llm_extract(client, request_text)
    account_id = str(extracted["account_id"]).strip()
    product = str(extracted["product"]).strip()
    qty_raw = extracted.get("quantity", None)

    # Step 3 — third-party service lookup (code)
    acct = http_get(f"/account/{account_id}")
    tier = acct["tier"]

    # Step 4 — reference store query (code)
    unit_price = query_price(product)
    sla_hours = query_sla(tier)

    # Step 5 — compute, applying the default-quantity rule (code)
    quantity = int(qty_raw) if qty_raw not in (None, "", "null") else DEFAULT_QTY
    subtotal = round(unit_price * quantity, 2)

    # Steps 6-8 — stacking discounts (code)
    volume_discount_pct = 10 if quantity >= 20 else 0
    tier_discount_pct = 5 if tier == "Enterprise" else 0
    total = round(subtotal * (1 - volume_discount_pct / 100) * (1 - tier_discount_pct / 100), 2)

    # Step 9 — branch on POST-discount total (code)
    decision = "ESCALATE" if (tier == "Enterprise" and total > THRESHOLD) else "STANDARD"

    # cognitive: classify (LLM)
    category, _ = llm_classify(client, request_text)

    # assemble + summary (LLM) + validate + (caller writes file)
    result = {
        "account_id": account_id,
        "category": category,
        "tier": tier,
        "unit_price": unit_price,
        "quantity": quantity,
        "subtotal": subtotal,
        "volume_discount_pct": volume_discount_pct,
        "tier_discount_pct": tier_discount_pct,
        "total": total,
        "sla_hours": sla_hours,
        "decision": decision,
    }
    result["summary"] = llm_summary(client, result)
    result["_model"] = model_id
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=20)
    ap.add_argument("--cases", nargs="*", default=None, help="subset of case ids")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--workers", type=int, default=8, help="concurrent requests")
    ap.add_argument("--check", action="store_true",
                    help="one rep/case; assert gradeable fields == ground truth")
    args = ap.parse_args()

    client = get_client()
    cases = args.cases or sorted(FX["cases"].keys())

    if args.check:
        truth = ground_truth()
        ok = True
        for cid in cases:
            res = run_pipeline(client, cid)
            diff = {k: (res.get(k), truth[cid][k]) for k in GRADEABLE_FIELDS if res.get(k) != truth[cid][k]}
            status = "OK" if not diff else f"MISMATCH {diff}"
            print(f"[check] {cid} model={res['_model']} -> {status}")
            ok = ok and not diff
        sys.exit(0 if ok else 1)

    out_dir = args.out_dir or os.path.join(ROOT, "results", "option2")

    def one_run(cid, i):
        try:
            res = run_pipeline(client, cid)
        except Exception as e:  # capture failures as a result so metrics see them
            res = {"_error": f"{type(e).__name__}: {e}"}
        ok, errs = (False, ["error"]) if "_error" in res else validate(res)
        res["_valid"] = ok
        res["_validation_errors"] = errs if not ok else []
        cdir = os.path.join(out_dir, cid)
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, f"run_{i:03d}.json"), "w") as fh:
            json.dump(res, fh, indent=2)
        return cid, i, ("valid" if ok else "INVALID")

    jobs = [(cid, i) for cid in cases for i in range(args.reps)]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for cid, i, verdict in pool.map(lambda a: one_run(*a), jobs):
            print(f"[{cid}] rep {i} -> {verdict}")
    print(f"Option 2 done -> {out_dir}")


if __name__ == "__main__":
    main()
