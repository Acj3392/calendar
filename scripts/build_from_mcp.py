#!/usr/bin/env python3
"""Transform a Monarch MCP get_transactions dump into data/spending.json.

The Monarch Money MCP connector returns transactions as
  {"result": "<json-string>"}  where the inner JSON is
  {"tool":..., "total_count":N, "data":[ {date, amount, category, merchant, ...} ]}

We keep both debits (spend) and credits (income, refunds), excluding transfers
and credit-card payments (which just move money between accounts). Output shape
matches what index.html expects (see scripts/aggregate.py).

Usage:
    python scripts/build_from_mcp.py <raw_mcp_dump.txt> [--today YYYY-MM-DD]
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from aggregate import aggregate_by_day

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


def _existing_budgets() -> dict:
    """Carry forward the budgets block from the current spending.json if present.

    The manual path has no live API access, so fetch_monarch.py (twice daily) is
    the authoritative budget source. Preserving the existing block ensures a manual
    transaction rebuild never silently wipes it.
    """
    try:
        return json.loads(OUT_PATH.read_text()).get("budgets", {})
    except Exception:  # noqa: BLE001 - missing / malformed file is fine
        return {}


def build(transactions: list, today: str) -> dict:
    normalized = []
    for t in transactions:
        category = t.get("category") or "Uncategorized"
        if category in EXCLUDED_CATEGORIES:
            continue
        if t.get("hide_from_reports"):
            continue
        amount = t.get("amount")
        if amount is None:
            continue
        # Preserve Monarch's sign (outflow negative, inflow positive);
        # aggregate_by_day() tags debit/credit and stores positive magnitudes.
        merchant = t.get("merchant") or t.get("plaid_description") or "Unknown"
        normalized.append(
            {"date": t["date"], "merchant": merchant, "amount": amount, "category": category}
        )

    data = aggregate_by_day(normalized)

    return {
        "today": today,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "refreshStatus": "ok",
        "budgets": _existing_budgets(),
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
