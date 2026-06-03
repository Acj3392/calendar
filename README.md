# The Daily Spend

A personal spending calendar that visualizes daily spending across Today / Week /
Month / Year views, styled as a personal-finance **newspaper**. Spend status reads
at a glance: days fill **rust-red** when you overspent, a **lime wash** when you
met your goal, neutral when on pace. Data comes from Monarch Money.

> Personal financial data — the Vercel deployment is password-gated.

## How it works

```
Monarch Money  →  scripts/fetch_monarch.py (or build_from_mcp.py)
               →  commits data/spending.json
               →  push to main triggers a Vercel redeploy
index.html (static)  →  fetches data/spending.json on load and renders
```

No database, no backend, **no build step**. `index.html` is the whole app (React
via CDN + in-browser Babel). The only thing that changes between deploys is
`data/spending.json`.

## Design

"The Daily Spend" — a Broadsheet newspaper crossed with a type foundry. Light
"Day Edition" + dark "Night Edition" (toggle in the gear menu).

- **Type:** Anton (masthead), Fraunces (numerals, italic when large), Syne
  (labels), Inter (body).
- **Color, semantic:** periwinkle = structure / today · acid-lime = met goal /
  active filter · rust-red = overspent.
- **Verdict system** drives the heatmap fills from the low/high thresholds
  (adjustable in settings).
- **Category filters** recompute every view live.
- **Robust by design:** pinned + SRI'd CDN runtime, React error boundary,
  validated data, fetch retry, and a stale/auth-failed "Stop Press" banner.

## Files

| Path | Purpose |
|------|---------|
| `index.html` | The whole app (React via CDN, no build). Fetches `data/spending.json`. |
| `data/spending.json` | Committed spending data — the refreshed artifact. |
| `scripts/fetch_monarch.py` | Token-auth pull from Monarch → writes `data/spending.json`. |
| `scripts/build_from_mcp.py` | Transforms a Monarch MCP dump → `data/spending.json`. |
| `scripts/refresh_local.sh` | Run by the daily launchd job. |
| `tests/smoke.spec.js` | Playwright smoke (zero console errors, all views × editions). |
| `vercel.json` | Static deploy config; marks the data file non-cacheable. |
| `docs/HANDOFF.md` | **Start here** — current state + what's next. |
| `docs/solutions/` | Compounded learnings (theming, auth, design tokens, testing). |

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
MST → `fetch_monarch.py` (token auth) → commits + pushes → Vercel redeploys.

**On-demand (Claude session):** pull recent transactions via the Monarch MCP,
then:
```bash
python scripts/build_from_mcp.py <mcp_dump.txt> --today $(date +%F)
git add data/spending.json && git commit -m "refresh" && git push
```

If the app shows a "Token expired" banner, re-authenticate — see
`docs/solutions/monarch-auth-and-refresh.md`. `MONARCH_TOKEN` lives in
`.env.local` (gitignored, never committed).

> **Why no scheduled GitHub Action?** The unofficial `monarchmoney` library is
> blocked from cloud IPs (HTTP 405/429), so cron-from-CI doesn't work. Refresh
> runs from the Mac (launchd) or a Claude session instead. `.github/workflows/
> refresh.yml` is kept for manual dispatch only.

## Deploy (Vercel)

- Framework preset **Other** (static, no build command).
- **Deployment Protection → on for production** — keep this gated.

## Caveats

- **Auth is the hard part.** Monarch has no public API; reliable auth is
  token-based from the Mac or the MCP connector, not cloud CI.
- **Spending only (for now).** Income, transfers, and credit-card payments are
  excluded so totals reflect real outflow. *Adding credits alongside debits is
  the next planned feature — see `docs/HANDOFF.md`.*
