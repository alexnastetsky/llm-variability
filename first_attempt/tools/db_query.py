#!/usr/bin/env python3
"""Deterministic reference-store queries against data/refdb.sqlite.

CLI:    python3 tools/db_query.py pricebook GADGET-X   -> 999.99
        python3 tools/db_query.py sla Enterprise       -> 4
Import: from tools.db_query import query_price, query_sla
"""
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "..", "data", "refdb.sqlite")


def _conn():
    return sqlite3.connect(DB_PATH)


def query_price(product: str):
    """Unit price for a product, or None if not found."""
    with _conn() as c:
        row = c.execute("SELECT unit_price FROM pricebook WHERE product = ?", (product,)).fetchone()
    return row[0] if row else None


def query_sla(tier: str):
    """SLA hours for a tier, or None if not found."""
    with _conn() as c:
        row = c.execute("SELECT hours FROM sla WHERE tier = ?", (tier,)).fetchone()
    return row[0] if row else None


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: db_query.py {pricebook <product> | sla <tier>}", file=sys.stderr)
        sys.exit(2)
    table, key = sys.argv[1], sys.argv[2]
    if table == "pricebook":
        val = query_price(key)
    elif table == "sla":
        val = query_sla(key)
    else:
        print(f"unknown table: {table}", file=sys.stderr)
        sys.exit(2)
    if val is None:
        print(f"not found: {table}/{key}", file=sys.stderr)
        sys.exit(1)
    print(val)
