#!/usr/bin/env python3
"""Pull recent Monarch Money transactions and write data/spending.json.

Auth (set as GitHub Actions secrets). Two modes — token is strongly preferred:

  MONARCH_TOKEN        a saved session token minted locally via scripts/mint_token.py.
                       Used as-is, so the scheduled job never hits Monarch's login
                       endpoint (which 429s from cloud IPs). This is the path the
                       GitHub Action uses.

  -- OR, fallback for local runs only --
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
    lookback = int(os.environ.get("LOOKBACK_DAYS", "90"))
    token = os.environ.get("MONARCH_TOKEN") or None

    if token:
        # Token path: reuse a session minted locally — no login call, no 429.
        mm = MonarchMoney(token=token)
    else:
        # Fallback (local use): real login with email/password (+ MFA seed).
        email = os.environ["MONARCH_EMAIL"]
        password = os.environ["MONARCH_PASSWORD"]
        mfa_secret = os.environ.get("MONARCH_MFA_SECRET") or None
        mm = MonarchMoney()
        await mm.login(
            email,
            password,
            use_saved_session=False,
            save_session=False,
            mfa_secret_key=mfa_secret,
        )

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
        "refreshStatus": "ok",
        "data": data,
    }


# Error-message fragments that indicate the Monarch token/session is bad,
# vs. a transient network/other failure. The app's banner reads refreshStatus
# to tell "re-auth needed" apart from "a run was just missed".
_AUTH_HINTS = ("401", "403", "405", "429", "auth", "token", "login", "unauthor", "forbidden")


def _stamp_auth_failed() -> None:
    """Mark the existing spending.json as auth_failed without clobbering its data."""
    try:
        existing = json.loads(OUT_PATH.read_text())
    except Exception:  # noqa: BLE001 - nothing to update
        return
    existing["refreshStatus"] = "auth_failed"
    OUT_PATH.write_text(json.dumps(existing, indent=2))
    print("Marked existing data/spending.json refreshStatus=auth_failed", file=sys.stderr)


def main() -> int:
    try:
        payload = asyncio.run(fetch())
    except KeyError as e:
        print(f"Missing required env var: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 - surface any Monarch/auth failure to CI
        msg = str(e).lower()
        print(f"Fetch failed: {e}", file=sys.stderr)
        if any(h in msg for h in _AUTH_HINTS):
            _stamp_auth_failed()
        return 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {OUT_PATH} — {len(payload['data'])} days through {payload['today']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
