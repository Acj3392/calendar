#!/usr/bin/env python3
"""Transform a Monarch MCP get_transactions dump into data/spending.json.

The Monarch Money MCP connector returns transactions as
  {"result": "<json-string>"}  where the inner JSON is
  {"tool":..., "total_count":N, "data":[ {date, amount, category, merchant, ...} ]}

We keep only real outflow spending: negative amounts, excluding transfers and
credit-card payments (which just move money between accounts). Output shape
matches what index.html expects.

Usage:
    python scripts/build_from_mcp.py <raw_mcp_dump.txt> [--today YYYY-MM-DD]
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "spending.json"

# Categories that move money around rather than represent real spending.
EXCLUDED_CATEGORIES = {
    "Credit Card Payment",
    "Transfer",
    "Transfers",
    "Balance Adjustments",
}


def load_transactions(path: Path) -> list:
    raw = json.loads(path.read_text())
    inner = raw["result"] if "result" in raw else raw
    if isinstance(inner, str):
        inner = json.loads(inner)
    return inner["data"]


def build(transactions: list, today: str) -> dict:
    by_day = defaultdict(list)
    for t in transactions:
        category = t.get("category") or "Uncategorized"
        if category in EXCLUDED_CATEGORIES:
            continue
        if t.get("hide_from_reports"):
            continue
        amount = t.get("amount", 0.0)
        # Monarch: outflows are negative. We want spend only.
        if amount is None or amount >= 0:
            continue
        spend = round(-amount, 2)
        merchant = t.get("merchant") or t.get("plaid_description") or "Unknown"
        by_day[t["date"]].append(
            {"merchant": merchant, "amount": spend, "category": category}
        )

    data = []
    for date in sorted(by_day):
        txns = by_day[date]
        data.append(
            {
                "date": date,
                "total": round(sum(x["amount"] for x in txns), 2),
                "transactions": txns,
            }
        )

    return {
        "today": today,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "refreshStatus": "ok",
        "data": data,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump", help="path to the raw MCP get_transactions output")
    ap.add_argument("--today", default=datetime.now(timezone.utc).date().isoformat())
    args = ap.parse_args()

    txns = load_transactions(Path(args.dump))
    payload = build(txns, args.today)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2))

    # Aggregate stats only — never echo individual transactions.
    days = payload["data"]
    total = round(sum(d["total"] for d in days), 2)
    ntx = sum(len(d["transactions"]) for d in days)
    print(f"Wrote {OUT_PATH}")
    print(f"  spending days: {len(days)}")
    print(f"  transactions kept: {ntx} (of {len(txns)} pulled)")
    if days:
        print(f"  date range: {days[0]['date']} → {days[-1]['date']}")
    print(f"  total spend: ${total:,.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
