#!/usr/bin/env python3
"""Build data/refdb.sqlite (pricebook + sla tables) from fixtures.json.

Deterministic reference store for the experiment. Re-running rebuilds the DB
from scratch so contents are always identical.
"""
import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures.json")
DB_PATH = os.path.join(HERE, "refdb.sqlite")


def main():
    with open(FIXTURES) as f:
        fx = json.load(f)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE pricebook (product TEXT PRIMARY KEY, unit_price REAL NOT NULL)")
    cur.execute("CREATE TABLE sla (tier TEXT PRIMARY KEY, hours INTEGER NOT NULL)")

    cur.executemany(
        "INSERT INTO pricebook (product, unit_price) VALUES (?, ?)",
        list(fx["pricebook"].items()),
    )
    cur.executemany(
        "INSERT INTO sla (tier, hours) VALUES (?, ?)",
        list(fx["sla_hours_by_tier"].items()),
    )
    conn.commit()
    conn.close()
    print(f"Seeded {DB_PATH} with {len(fx['pricebook'])} products and {len(fx['sla_hours_by_tier'])} SLA tiers.")


if __name__ == "__main__":
    main()
