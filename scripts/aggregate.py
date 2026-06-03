#!/usr/bin/env python3
"""Shared day-aggregation for the spending pipeline.

Both fetch_monarch.py and build_from_mcp.py normalize their (differently shaped)
sources into a flat list of transactions carrying a SIGNED Monarch amount
(outflows negative, inflows positive), then call aggregate_by_day() to produce
the day records written to data/spending.json.

Output shape (Option A — positive amounts + explicit type, see
docs/plans/2026-06-03-credits-alongside-debits.md):
  { "date", "total"(spend, +), "received"(credits, +), "net"(received - total),
    "transactions": [ {merchant, amount(+), category, type:"debit"|"credit"} ] }

Callers exclude transfers / credit-card payments (EXCLUDED_CATEGORIES) before
calling this. amount == 0 transactions are skipped here.
"""
from collections import defaultdict


def aggregate_by_day(transactions):
    """Aggregate normalized transactions into sorted day records.

    transactions: iterable of {date, merchant, amount(signed float), category}.
    Returns a list of day records sorted ascending by date.
    """
    by_day = defaultdict(list)
    for t in transactions:
        amount = t.get("amount")
        if amount is None or amount == 0:
            continue
        is_credit = amount > 0
        by_day[t["date"]].append(
            {
                "merchant": t.get("merchant") or "Unknown",
                "amount": round(abs(amount), 2),
                "category": t.get("category") or "Uncategorized",
                "type": "credit" if is_credit else "debit",
            }
        )

    data = []
    for date in sorted(by_day):
        txns = by_day[date]
        total = round(sum(x["amount"] for x in txns if x["type"] == "debit"), 2)
        received = round(sum(x["amount"] for x in txns if x["type"] == "credit"), 2)
        data.append(
            {
                "date": date,
                "total": total,
                "received": received,
                "net": round(received - total, 2),
                "transactions": txns,
            }
        )
    return data


def _selftest():
    # debit + credit on one day, a pure-income day, a zero-amount skip
    rows = [
        {"date": "2026-06-02", "merchant": "Teos", "amount": -40.0, "category": "Restaurants & Bars"},
        {"date": "2026-06-02", "merchant": "Amazon Refund", "amount": 30.0, "category": "Shopping"},
        {"date": "2026-06-03", "merchant": "Payroll", "amount": 2000.0, "category": "Income"},
        {"date": "2026-06-03", "merchant": "Void", "amount": 0.0, "category": "Shopping"},
    ]
    data = aggregate_by_day(rows)
    assert [d["date"] for d in data] == ["2026-06-02", "2026-06-03"], data
    d0, d1 = data
    assert d0["total"] == 40.0 and d0["received"] == 30.0 and d0["net"] == -10.0, d0
    assert d0["transactions"][0]["type"] == "debit"
    assert d0["transactions"][1]["type"] == "credit" and d0["transactions"][1]["amount"] == 30.0
    # pure income: zero-amount tx skipped, so only Payroll remains
    assert d1["total"] == 0.0 and d1["received"] == 2000.0 and d1["net"] == 2000.0, d1
    assert len(d1["transactions"]) == 1
    print("aggregate_by_day self-test OK")


if __name__ == "__main__":
    _selftest()
