# The Daily Spend

A personal spending calendar that visualizes daily money across Today / Week /
Month / Year views, styled as a personal-finance **newspaper**. Each day reads at
a glance by **shape and color**: ▲ overspent (rust-red), ✓ met goal (lime wash),
– on pace, ● no spend, ✦ net positive. Money in (income, refunds) shows as teal
`+$` alongside spending. Data comes from Monarch Money.

> Personal financial data — the Vercel deployment is password-gated.

## How it works

```
Monarch Money  →  scripts/fetch_monarch.py (or build_from_mcp.py)
               →  scripts/aggregate.py (shared day-aggregation)
               →  commits data/spending.json
               →  push to main triggers a Vercel redeploy
index.html (static)  →  fetches data/spending.json on load and renders
```

No database, no backend, **no build step**. `index.html` is the whole app (React
via CDN + in-browser Babel). The only thing that changes between most deploys is
`data/spending.json`.

## Design

"The Daily Spend" — a Broadsheet newspaper crossed with a type foundry. Light
"Day Edition" + dark "Night Edition" (toggle in the gear menu).

- **Type:** Anton (masthead), Fraunces (numerals, italic when large), Syne
  (labels), Inter (body).
- **Color, semantic:** periwinkle = structure / today · acid-lime = met goal /
  active filter (fill-only) · rust-red = overspent · **teal = money in**.
- **Verdict, shape-first:** every populated cell carries a glyph
  (▲ – ✓ ● ✦) so the heatmap reads without relying on color (colorblind-safe);
  color reinforces. Tiers come from adjustable low/high thresholds.
- **Credits:** income and refunds render as teal `+$`. A day's detail is a
  **receipt** — Spending + Total Spent, Money In + Total Received, then **Net**
  (net spent, `total − received`, shown positive; net inflow shows `+$` teal).
- **Spend / Net basis toggle** (Settings → Verdict basis, persisted): Spend mode
  (default) judges and shows gross spend everywhere; Net mode makes net cost the
  headline + every cell number, so money-in offsets the day.
- **Category filters** recompute every view live; income categories appear as
  teal `+` chips (credit-only categories — refunds in spend categories stay on
  their debit chip).
- **Robust by design:** pinned + SRI'd CDN runtime, React error boundary,
  validated data, fetch retry, and a stale/auth-failed "Stop Press" banner.

## Files

| Path | Purpose |
|------|---------|
| `index.html` | The whole app (React via CDN, no build). Fetches `data/spending.json`. |
| `data/spending.json` | Committed spending data — the refreshed artifact. |
| `scripts/aggregate.py` | Shared `aggregate_by_day()` (tags debit/credit, computes total/received/net). Imported by both pipelines. |
| `scripts/fetch_monarch.py` | Token-auth pull from Monarch → writes `data/spending.json`. |
| `scripts/build_from_mcp.py` | Transforms a Monarch MCP dump → `data/spending.json`. |
| `scripts/refresh_local.sh` | Run by the daily launchd job. |
| `tests/smoke.spec.js` | Playwright smoke (zero console errors, all views × editions, credit + net assertions). |
| `tests/fixtures/spending.sample.json` | Deterministic fixture for credit/net tests (routed in, not the live window). |
| `vercel.json` | Static deploy config; marks the data file non-cacheable. |
| `docs/HANDOFF.md` | **Start here** — current state + ideas. |
| `docs/solutions/` | Compounded learnings (credits/net, theming, auth, design tokens, testing, CSS grid). |

## Develop

```bash
npm install            # dev/CI only — the app itself is no-build
npm run serve          # python http.server on :8899  → http://localhost:8899
npm test               # Playwright smoke (run `npm run test:install` once first)
git push origin main   # auto-deploys to Vercel
```

Chrome blocks `file://` fetch of the JSON, so use the local server (not `open
index.html`).

## Refreshing the data

**Daily (automatic):** a launchd job on the Mac runs `refresh_local.sh` at 9am
and 4pm local (America/Denver) → `fetch_monarch.py` (token auth) → commits + pushes →
Vercel redeploys. (If the repo lives under `~/Desktop`, the agent needs Full Disk
Access granted to `/bin/bash` or macOS TCC blocks it — see the auth solution doc.)

The window is **year-to-date** (Jan 1 of the current year → today), so every month
from January is populated; it resets each Jan 1. Set `MONARCH_START_DATE=YYYY-MM-DD`
to override (prior year, all history, etc.).

**On-demand (Claude session):** pull recent transactions via the Monarch MCP,
then:
```bash
python scripts/build_from_mcp.py <mcp_dump.txt> --today $(date +%F)
git add data/spending.json && git commit -m "refresh" && git push
```

If the app shows a "Token expired" banner, re-authenticate — see
`docs/solutions/monarch-auth-and-refresh.md`. `MONARCH_TOKEN` lives in
`.env.local` (gitignored, never committed).

> **Heads up (data vs. code ordering):** `refresh_local.sh` pushes
> `data/spending.json` on its own. If you change the data *shape*, land the
> matching `index.html` first or in the same push — a refresh firing in between
> serves new data with old code. Also `index.html` is not no-store cached (only
> the JSON is), so a code push may need a hard refresh to appear.

> **Why no scheduled GitHub Action?** The unofficial `monarchmoney` library is
> blocked from cloud IPs (HTTP 405/429), so cron-from-CI doesn't work. Refresh
> runs from the Mac (launchd) or a Claude session instead.

## Deploy (Vercel)

- Framework preset **Other** (static, no build command).
- **Deployment Protection → on for production** — keep this gated.

## What's included / excluded

- **Debits (spending) and credits (income, refunds)** are both shown. Credits are
  a teal, additive layer; the Spend/Net toggle decides whether they offset the
  day's headline.
- **Transfers and credit-card payments are excluded** (`EXCLUDED_CATEGORIES` in
  the scripts) — they move money between accounts and would double-count.
- **Auth is the hard part.** Monarch has no public API; reliable auth is
  token-based from the Mac or the MCP connector, not cloud CI.
