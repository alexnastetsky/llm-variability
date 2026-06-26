#!/usr/bin/env python3
"""Deterministic ground truth for each case, derived from data/fixtures.json.

Round 2: longer-horizon pipeline with stacking discounts. The escalation
decision depends on the POST-discount total, which depends on account->tier,
quantity (volume), and tier discount — a long-range chain.

Used only for GRADING — never given to the orchestrators that produce outputs.

CLI: python3 analysis/ground_truth.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "..", "data", "fixtures.json")

GRADEABLE_FIELDS = ["account_id", "category", "tier", "unit_price", "quantity",
                    "subtotal", "volume_discount_pct", "tier_discount_pct",
                    "total", "sla_hours", "decision"]


def _load():
    with open(FIXTURES) as f:
        return json.load(f)


def compute_case(fx, case_id):
    case = fx["cases"][case_id]
    rules = fx["rules"]
    account_id = case["account_id"]
    product = case["product"]
    quantity = case["quantity"]

    tier = fx["accounts"][account_id]["tier"]
    unit_price = fx["pricebook"][product]
    subtotal = round(unit_price * quantity, 2)

    volume_discount_pct = 10 if quantity >= 20 else 0
    tier_discount_pct = 5 if tier == "Enterprise" else 0
    total = round(subtotal * (1 - volume_discount_pct / 100) * (1 - tier_discount_pct / 100), 2)

    sla_hours = fx["sla_hours_by_tier"][tier]
    threshold = rules["escalation_threshold"]
    decision = "ESCALATE" if (tier == "Enterprise" and total > threshold) else "STANDARD"

    return {
        "account_id": account_id,
        "category": case["expected_category"],
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


def ground_truth():
    fx = _load()
    return {cid: compute_case(fx, cid) for cid in fx["cases"]}


if __name__ == "__main__":
    print(json.dumps(ground_truth(), indent=2))
