#!/usr/bin/env python3
"""Schema + internal-consistency validator for a pipeline result object.

Checks STRUCTURE and self-consistency only (no ground-truth knowledge), so it is
safe to give to Option 1's validation loop:
  - all required fields present with correct types
  - enums valid (category, tier, decision)
  - quantity >= 1, unit_price > 0
  - total == round(unit_price * quantity, 2)   (internal consistency)

CLI:    python3 tools/validate_json.py result.json     (or '-' for stdin)
        exit 0 = valid, exit 1 = invalid (errors printed)
Import: from tools.validate_json import validate
"""
import json
import sys

CATEGORIES = {"billing", "technical", "sales", "complaint"}
TIERS = {"Enterprise", "Standard", "Free"}
DECISIONS = {"ESCALATE", "STANDARD"}
REQUIRED = ["account_id", "category", "tier", "unit_price", "quantity",
            "subtotal", "volume_discount_pct", "tier_discount_pct", "total",
            "sla_hours", "decision", "summary"]


def validate(obj):
    """Return (ok: bool, errors: list[str])."""
    errors = []
    if not isinstance(obj, dict):
        return False, ["result is not a JSON object"]

    for field in REQUIRED:
        if field not in obj:
            errors.append(f"missing field: {field}")
    if errors:
        return False, errors

    if not (isinstance(obj["account_id"], str) and obj["account_id"].startswith("ACC-")):
        errors.append("account_id must be a string like 'ACC-1234'")
    if obj["category"] not in CATEGORIES:
        errors.append(f"category must be one of {sorted(CATEGORIES)}")
    if obj["tier"] not in TIERS:
        errors.append(f"tier must be one of {sorted(TIERS)}")
    if obj["decision"] not in DECISIONS:
        errors.append(f"decision must be one of {sorted(DECISIONS)}")
    if not isinstance(obj["unit_price"], (int, float)) or obj["unit_price"] <= 0:
        errors.append("unit_price must be a positive number")
    if not isinstance(obj["quantity"], int) or obj["quantity"] < 1:
        errors.append("quantity must be an integer >= 1")
    if not isinstance(obj["sla_hours"], int) or obj["sla_hours"] < 1:
        errors.append("sla_hours must be a positive integer")
    for fld in ("subtotal", "total"):
        if not isinstance(obj[fld], (int, float)) or obj[fld] < 0:
            errors.append(f"{fld} must be a non-negative number")
    for fld in ("volume_discount_pct", "tier_discount_pct"):
        if not isinstance(obj[fld], (int, float)) or not (0 <= obj[fld] <= 100):
            errors.append(f"{fld} must be a number between 0 and 100")
    if not isinstance(obj["summary"], str) or not obj["summary"].strip():
        errors.append("summary must be a non-empty string")

    # internal consistency: subtotal = unit_price*quantity; total = subtotal after stacked discounts
    if not errors:
        exp_subtotal = round(obj["unit_price"] * obj["quantity"], 2)
        if abs(round(obj["subtotal"], 2) - exp_subtotal) > 0.01:
            errors.append(f"subtotal ({obj['subtotal']}) != unit_price*quantity ({exp_subtotal})")
        exp_total = round(obj["subtotal"] * (1 - obj["volume_discount_pct"] / 100)
                          * (1 - obj["tier_discount_pct"] / 100), 2)
        if abs(round(obj["total"], 2) - exp_total) > 0.01:
            errors.append(f"total ({obj['total']}) != subtotal after discounts ({exp_total})")

    return (len(errors) == 0), errors


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: validate_json.py <file|->", file=sys.stderr)
        sys.exit(2)
    raw = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1]).read()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"INVALID: not parseable JSON: {e}", file=sys.stderr)
        sys.exit(1)
    ok, errs = validate(obj)
    if ok:
        print("VALID")
        sys.exit(0)
    print("INVALID:\n  - " + "\n  - ".join(errs), file=sys.stderr)
    sys.exit(1)
