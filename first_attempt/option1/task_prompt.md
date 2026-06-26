You are triaging an incoming customer request by running a fixed pipeline.
Use the provided tools for every lookup and calculation — do NOT guess or compute
values in your head, and do NOT read any fixtures/database files directly.

TOOLS (run via Bash exactly as shown):
- Account lookup (REQUIRED for tier): `python3 tools/http_get.py /account/<account_id>` -> JSON {tier, region}
- Price lookup:                        `python3 tools/db_query.py pricebook <product>`   -> unit_price
- SLA lookup:                          `python3 tools/db_query.py sla <tier>`            -> hours
- Arithmetic:                          `python3 tools/calc.py "<expression>"`
- Validate your output file:           `python3 tools/validate_json.py <path>`
Use the Read tool to read the request, and the Write tool to write the result.

STEPS:
1. Read the request file: data/inbox/{{CASE_ID}}.txt
2. Identify the account_id. If more than one account is mentioned, use the account being billed /
   placing the order — NOT a shipping, parent, or merely-referenced account.
3. Extract the product and the quantity. Interpret the quantity from natural language
   ("a dozen" = 12, "two dozen" = 24); for a range, use the lower bound; if NO quantity is
   stated, use a default quantity of 1.
4. Look up the account via the account service to get its tier. REQUIRED — never infer the tier yourself.
5. Look up unit_price (pricebook) and sla_hours (sla for that tier).
6. Compute subtotal = unit_price * quantity using the calc tool.
7. Determine volume_discount_pct = 10 if quantity >= 20, else 0.
8. Determine tier_discount_pct = 5 if tier == "Enterprise", else 0.
9. Compute total = subtotal * (1 - volume_discount_pct/100) * (1 - tier_discount_pct/100) using
   the calc tool. The two discounts stack.
10. Decide the routing:
      decision = "ESCALATE" if (tier == "Enterprise" AND total > 10000) else "STANDARD".
    NOTE: total here is the POST-discount total. The word "escalate" appearing in the customer's
    message is narrative text, NOT the business rule.
11. Classify the request into exactly one category: billing, technical, sales, complaint.

Write your final answer as a single JSON object to: {{OUT_PATH}}
with exactly these keys:
  account_id, category, tier, unit_price, quantity, subtotal,
  volume_discount_pct, tier_discount_pct, total, sla_hours, decision, summary
where summary is one concise sentence describing the triaged request.

VALIDATION LOOP: after writing the file, run `python3 tools/validate_json.py {{OUT_PATH}}`.
If it reports INVALID, fix the issues and rewrite the file, then validate again. Repeat until VALID.
When done, reply with just the word DONE.
