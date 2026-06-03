---
title: "Getting live Monarch Money data into a static app — what works, what's dead"
date: 2026-06-01
tags: [integration, auth, monarch, mcp, deployment, workaround]
category: workaround
module: deployment
symptoms: ["HTTP 405 Method Not Allowed on Monarch login", "HTTP 429 Too Many Requests from GitHub Actions", "MCP get_transactions returns 401 Unauthorized", "no auth token in browser localStorage", "monarchmoney login fails from cloud IP"]
---

# Getting live Monarch Money data into a static app

The hard part of this project was never the UI — it was **authenticating to
Monarch Money**, which has no official public API. This documents every approach
that failed and the one that works, so we never re-run the multi-hour
investigation. The end product is a static `index.html` that renders a committed
`data/spending.json`; the only real question is how that JSON gets refreshed.

## Problem

Goal: pull my real transactions from Monarch on a schedule and show them in a
calendar deployed on Vercel. Monarch has **no official API**, so every option is
a workaround, and most of them are now blocked.

## What's DEAD (don't try these again)

### 1. The `monarchmoney` Python library login — DEAD
- `monarchmoney` (community lib, 0.1.15 = latest) calls `POST /auth/login/`.
- **Locally:** returns **HTTP 405 Method Not Allowed** — Monarch changed the
  endpoint/method; the library is broken at the API level. Adding a real browser
  `User-Agent` + `Origin` + `device-uuid` headers did **not** fix the 405.
- **From GitHub Actions (cloud IP):** returns **HTTP 429 Too Many Requests** —
  Monarch's edge rate-limits/ blocks datacenter IPs outright.
- Net: **a scheduled GitHub Action can never authenticate.** This is why the cron
  in `.github/workflows/refresh.yml` is disabled (`workflow_dispatch` only),
  kept solely in case the library login is ever restored.

### 2. Browser token extraction — DEAD
- Monarch stores its auth token in an **httpOnly cookie**, *not* localStorage.
  A full localStorage scan shows only device IDs, Plaid link tokens, and
  analytics IDs — no usable session token.
- Extracting session tokens is also (correctly) blocked by the assistant's
  safety classifier. Don't route financial credentials through the chat/JS.

### 3. Minting a long-lived token locally — DEAD
- `scripts/mint_token.py` tried to log in once and emit a token for CI. It fails
  for the same reason as #1 (the library's login 405s). Abandoned; kept for
  reference only.

## What WORKS: the Monarch MCP connector

Authentication only succeeds from an **interactive Claude session via the Monarch
MCP connector** (`mcp__Monarch_Money__*`). The connector is authenticated by a
standalone script, **not** by the library's normal login.

### The key insight — the real device UUID
`login_setup.py` (in `/Users/anna/Desktop/Home/PersonalOS/Ideas/Project/`)
authenticates where generic scripts fail because its `browserize()` helper sends:
- the **real `monarchDeviceUUID`** copied from the browser's localStorage, stored
  as `MONARCH_DEVICE_UUID` in that project's `.env` (never committed), plus
- a real browser `User-Agent` and `Origin: https://app.monarch.com`.

Monarch's edge (Cloudflare bot check) trusts a *known* device UUID. Generic
scripts use a random/empty UUID → blocked. **This is the whole trick.**

The script saves the session into the **system keyring** via
`secure_session.save_authenticated_session(mm)`.

### Gotcha: the MCP server caches the token in memory at startup
After (re-)running `login_setup.py`, the MCP server is still holding the **old**
token in memory. Symptom: `get_transactions` returns **401 Unauthorized**.
**Fix: fully quit and reopen Claude Desktop** so the MCP server reloads the fresh
token from the keyring on startup. (Reconnecting the server is not enough if the
app process kept the old one.)

## What WORKS: local launchd daily refresh (2026-06-02 addition)

A second working path was established: a **local Mac launchd job** that runs
`scripts/refresh_local.sh` at 9am daily. It authenticates via a saved
`MONARCH_TOKEN` (not email/password login), so it bypasses Monarch's login
endpoint entirely.

### How it works
1. `.env.local` holds `MONARCH_TOKEN=<value>` — sourced at runtime, never committed.
2. The token is extracted from the macOS keychain at startup:
   ```bash
   security find-generic-password -s "com.mcp.monarch-mcp-server" -a "monarch-token" -w
   # OR file fallback:
   cat ~/.monarch-mcp-server/token
   ```
3. `scripts/fetch_monarch.py` uses the `MONARCH_TOKEN` path (no login call).
4. On success, commits `data/spending.json` and pushes → Vercel redeploys.

### Critical: use the PersonalOS venv, not the calendar project venv
The calendar project has a stale `.venv` (Python 3.9, `monarchmoney==0.1.15`).
**0.1.15 breaks with token auth** (`execute_async()` missing argument error).
The working version is **1.3.0**, installed in the PersonalOS project's venv:
```
/Users/anna/Desktop/Home/PersonalOS/Ideas/Project/.venv/bin/python
```
`refresh_local.sh` is wired to use this venv explicitly. **1.3.0 is NOT on PyPI** —
it's a local/community build; `pip install 'monarchmoney>=1.3.0'` will fail.

### launchd: use `-l` flag on bash or get "Operation not permitted"
The plist must invoke bash with the login flag so it loads the user environment:
```xml
<key>ProgramArguments</key>
<array>
  <string>/bin/bash</string>
  <string>-l</string>
  <string>/full/path/to/refresh_local.sh</string>
</array>
```
Without `-l`, launchd returns "Operation not permitted" on the script.

### Token expiry
The `MONARCH_TOKEN` session will eventually expire. When it does:
- `logs/refresh.log` will show `Fetch failed: ...` (HTTP 401 or similar)
- The app will show an amber stale-data banner after 26h without a refresh
- Fix: open a Claude session → re-authenticate via Monarch MCP login tool →
  re-extract the new token into `.env.local` (same `~/.monarch-mcp-server/token`
  path) → restart the launchd agent.

## The refresh model: ON-DEMAND (not cron)

Because auth lives in a Claude session, refresh is manual/on-demand:

```
MCP get_transactions  (save the raw dump to a file)
  → python scripts/build_from_mcp.py <dump> --today $(date +%F)
  → commit + push data/spending.json
  → Vercel auto-redeploys
```

### `build_from_mcp.py` transform rules
- Input shape: `{"result": "<json-string>"}` where the inner JSON has `data: [...]`.
- **Exclude** categories that just move money: `Credit Card Payment`, `Transfer`,
  `Transfers`, `Balance Adjustments`, plus anything with `hide_from_reports`.
- **Spend only:** keep negative amounts, store as positive (`spend = -amount`).
- Group by date → `{date, total, transactions:[{merchant, amount, category}]}`.
- Prints **aggregate stats only** (days, tx count, total, range) — never echoes
  individual transactions. Keep it that way (personal financial data).

## Deployment notes
- Vercel import preset = **Other** (static site), **not** Python. No build command.
- **Deployment Protection ON** for production — this is personal financial data;
  keep it gated, never public. (Disable in project settings, not via `vercel.json`.)
- `vercel.json` marks `/data/spending.json` no-cache so refreshes show immediately.

## Why It Works
Monarch authenticates the *device*, not just the credentials. A session minted
from the genuine browser device UUID + browser headers passes the edge check; a
datacenter IP or unknown device does not. The MCP connector keeps that session
alive in the keyring, so a Claude session can pull live data on demand — the one
context that satisfies Monarch's checks.

## Gotcha (2026-06-03): a data refresh can outrun the UI code

`refresh_local.sh` commits + pushes `data/spending.json` on its own. During the
credits work it ran mid-feature and pushed **new-shape data ahead of the
matching `index.html`**, so production briefly served old UI + new data
(credits rendered as plain spend rows; category filters inflated totals). The
old code was backward-tolerant enough not to crash, which made it easy to miss.

Lesson: when a data-shape change is in flight, **land the UI code first (or in
the same push)**. If a refresh fires in between, expect prod to render the new
data with old code until the code catches up. Also note `index.html` is *not*
no-store cached (only `/data/spending.json` is), so a code push needs a hard
refresh to appear even after Vercel reports success.

## Related
- `README.md` — happy-path setup & refresh steps
- `scripts/build_from_mcp.py` — the transform
- `scripts/fetch_monarch.py`, `scripts/mint_token.py` — the dead library path (reference)
- `.github/workflows/refresh.yml` — disabled cron (kept for if library login returns)
- `docs/solutions/no-build-theming-and-chrome.md` — the UI/theming patterns
