#!/usr/bin/env python3
"""Pull recent Monarch Money transactions and write data/spending.json.

Auth comes from environment variables (set as GitHub Actions secrets):
  MONARCH_EMAIL        your Monarch login email
  MONARCH_PASSWORD     your Monarch password
  MONARCH_MFA_SECRET   the TOTP setup secret from Monarch's authenticator setup
                       (lets this script generate the 6-digit code unattended)

Optional:
  LOOKBACK_DAYS        how many days of history to include (default 90)

The output shape matches what index.html expects:
  { "today": "YYYY-MM-DD", "generatedAt": "<iso>", "data": [
      { "date": "YYYY-MM-DD", "total": <float>,
        "transactions": [ { "merchant": str, "amount": float, "category": str } ] }
  ] }
Days are sorted ascending. Only spending is counted: positive outflows,
excluding transfers and credit-card payments (which net to zero, not spend).
"""

import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from monarchmoney import MonarchMoney

# Categories that move money around rather than represent real spending.
EXCLUDED_CATEGORIES = {"Credit Card Payment", "Transfer", "Transfers", "Balance Adjustments"}

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "spending.json"


async def fetch() -> dict:
    email = os.environ["MONARCH_EMAIL"]
    password = os.environ["MONARCH_PASSWORD"]
    mfa_secret = os.environ.get("MONARCH_MFA_SECRET")
    lookback = int(os.environ.get("LOOKBACK_DAYS", "90"))

    mm = MonarchMoney()
    await mm.login(email, password, mfa_secret_key=mfa_secret)

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=lookback)

    # Page through results so we don't miss days with many transactions.
    results = []
    offset = 0
    page = 500
    while True:
        resp = await mm.get_transactions(
            limit=page,
            offset=offset,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
        )
        batch = resp["allTransactions"]["results"]
        results.extend(batch)
        total_count = resp["allTransactions"]["totalCount"]
        offset += len(batch)
        if not batch or offset >= total_count:
            break

    by_day = defaultdict(list)
    for t in results:
        category = (t.get("category") or {}).get("name", "Uncategorized")
        if category in EXCLUDED_CATEGORIES:
            continue
        amount = t.get("amount", 0.0)
        # Monarch: expenses are negative, income positive. We want spend only.
        if amount >= 0:
            continue
        spend = round(-amount, 2)
        merchant = (t.get("merchant") or {}).get("name") or t.get("plaidName") or "Unknown"
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
        "today": end.isoformat(),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


def main() -> int:
    try:
        payload = asyncio.run(fetch())
    except KeyError as e:
        print(f"Missing required env var: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 - surface any Monarch/auth failure to CI
        print(f"Fetch failed: {e}", file=sys.stderr)
        return 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {OUT_PATH} — {len(payload['data'])} days through {payload['today']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
