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
  MONARCH_START_DATE   YYYY-MM-DD; overrides the window start. Without it the window
                       is year-to-date (Jan 1 of the current year → today), so every
                       month from January is pulled. A malformed value fails loud
                       (ValueError → non-zero exit), never silently falls back.

Note: this (token) path defines the window. The manual MCP path
(scripts/build_from_mcp.py) has NO window — it transforms whatever the operator
pulled in the Claude session, so query Jan 1 → today there to match.

The output shape matches what index.html expects (see scripts/aggregate.py):
  { "today": "YYYY-MM-DD", "generatedAt": "<iso>", "data": [
      { "date": "YYYY-MM-DD", "total": <spend>, "received": <credits>, "net": <recv-total>,
        "transactions": [ { "merchant": str, "amount": float, "category": str,
                            "type": "debit"|"credit" } ] }
  ] }
Days are sorted ascending. Both debits (spend) and credits (income, refunds) are
kept; transfers and credit-card payments are excluded (they net to zero).
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from monarchmoney import MonarchMoney

from aggregate import aggregate_by_day, compute_window

# Categories that move money around rather than represent real spending.
EXCLUDED_CATEGORIES = {"Credit Card Payment", "Transfer", "Transfers", "Balance Adjustments"}

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "spending.json"


async def fetch() -> dict:
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

    # Year-to-date by default (Jan 1 → today); MONARCH_START_DATE overrides it.
    end = datetime.now(timezone.utc).date()
    start, _ = compute_window(end, os.environ.get("MONARCH_START_DATE"))

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

    normalized = []
    for t in results:
        category = (t.get("category") or {}).get("name", "Uncategorized")
        if category in EXCLUDED_CATEGORIES:
            continue
        # Preserve Monarch's sign (outflow negative, inflow positive);
        # aggregate_by_day() tags debit/credit and stores positive magnitudes.
        amount = t.get("amount", 0.0)
        merchant = (t.get("merchant") or {}).get("name") or t.get("plaidName") or "Unknown"
        normalized.append(
            {"date": t["date"], "merchant": merchant, "amount": amount, "category": category}
        )

    data = aggregate_by_day(normalized)

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
