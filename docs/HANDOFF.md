# The Daily Spend — Handoff

> Pass this to the next session. It's the current source of truth for state +
> what's next. If anything here conflicts with the actual files, trust the files.
> Last updated: 2026-06-03.

---

## What this is

A personal spending calendar for Anna. **Single static `index.html`** — React
via CDN + in-browser Babel, **no build step, no backend, no database**. It fetches
`data/spending.json` and renders Today / Week / Month / Year views. Hosted on
Vercel (password-gated — personal financial data). Repo: `annajay778/calendar`.

**Live now on `main`** (auto-deploys to Vercel on push; direct-to-main is
authorized for this repo):
- `222c8d3` redesign + robustness · `35c268e` filters + verdict · `a6c097b`
  review fix · `8a5d802` docs

Gated URL: `https://calendar-anna-8858s-projects.vercel.app`
(MCP `list_projects` doesn't surface it; find via
`gh api repos/annajay778/calendar/deployments`).

---

## Current design — "The Daily Spend"

A personal-finance **newspaper** (Broadsheet) crossed with a **type foundry**
(Specimen). Both light "Day Edition" and dark "Night Edition".

- **Type:** Anton = masthead nameplate only · Fraunces = all numerals (italic
  when large) · Syne = labels/kickers/section heads · Inter = body/UI.
- **Color (semantic, single source):** periwinkle `#6c5cf6` = structure / today /
  links · acid-lime = "good / met goal / active filter" **(fill-only — lime text
  fails contrast)** · rust-red = **overspent**.
- **Verdict system:** spend tiers (low/medium/high) map to a clear
  Met goal ✓ / On pace / Overspent signal. Heatmap cells **fill** by verdict
  (red block = over, lime wash = good) so status reads at a glance. Today is a
  periwinkle ring layered over the verdict fill.
- **Category filters:** scrollable chips; selecting categories recomputes every
  view + total + heatmap via the `viewDay()` helper.
- **Robustness:** pinned production React/Babel + SRI; `ErrorBoundary`;
  `spending.json` validated on load; fetch retry; threshold clamp;
  `refreshStatus` errata strip (token-expired vs missed-run).
- **Tests:** `tests/smoke.spec.js` (Playwright) + `.github/workflows/smoke.yml`.
  Run `npm test`. Serves via `python3 -m http.server 8899`.

**Read these before changing the UI** (they'll save you a rediscovery):
- `docs/solutions/design-tokens-and-verdict-encoding.md` — the token + verdict pattern
- `docs/solutions/no-build-theming-and-chrome.md` — the `THEMES[mode]` foundation
- `docs/solutions/smoke-test-fixed-data-blind-spots.md` — testing gotcha
- `docs/design/aspirational-direction.md` — the design north star
- `docs/design/mockups.html` — the three explored directions (open in a browser)

---

## ✅ SHIPPED: credits alongside debits (2026-06-03)

Credits (income, refunds) are now in end to end, plus a Spend/Net verdict toggle.
**Read `docs/solutions/credits-and-net-basis.md` first** — it's the authoritative
write-up. Highlights:
- **Data shape:** transactions are positive `amount` + `type:"debit"|"credit"`;
  days carry `total` (gross spend), `received`, `net`. Shared `scripts/aggregate.py`
  feeds both pipeline scripts.
- **Net is "net spent"** (`total − received`, positive). A Spend/Net toggle
  (`scVerdictBasis`, default spend) routes through `basisAmount(dd)`: Net mode makes
  net cost the headline + every cell number; Spend mode is unchanged.
- **Heatmap reads by shape now:** verdict glyphs ▲ – ✓ ● ✦ (`verdictOf().mark`),
  with repaired Night-edition tints. Credit chips list income-only categories.
- Tests: `tests/fixtures/spending.sample.json` + fixture-routed credit assertions.

Gotchas captured this session: [[css-grid-1fr-overflow]] (use `minmax(0,1fr)`),
the fixture-overlap blind spot ([[smoke-test-fixed-data-blind-spots]]), and the
refresh-outran-the-code deploy ordering note ([[monarch-auth-and-refresh]]).

## ✅ SHIPPED: Category budget goal in Focus mode (2026-06-06)

Focusing a category with a Monarch budget shows "$spent of $budget · on track /
ahead of pace / over budget" in the Month + Today headers (reads the `budgets` block
in `spending.json`). Replaces the relative "vs avg" strip text when active. **Read
`docs/solutions/goal-color-off-full-budget-not-pace.md`** — the lesson is color the
alarm off the full budget (unambiguous), never a linear pace line (cries wolf on
bursty data); pace is text only. Week/Year deferred (budgets cover 3 months).
`index.html`: `budgetStatus`, `BudgetLine`.

## ✅ SHIPPED: Year-to-date data window (2026-06-05)

The Monarch fetch window changed from a trailing 90 days to **year-to-date** (Jan 1 →
today), so every month from January is populated (resets each Jan 1;
`MONARCH_START_DATE` overrides). Logic is a pure `compute_window()` in `aggregate.py`
with a selftest. **Read `docs/solutions/backfill-vs-window-on-overwriting-jobs.md`** —
the lesson is that a backfill won't stick when a scheduled job overwrites its output;
you change the window, not the data. Verified on both refresh paths.

## ✅ SHIPPED: "Not applicable" categories (2026-06-05)

Mark categories (e.g. Mortgage) as not-applicable in Settings → they drop from every
total/net/verdict across all views, both directions, but stay listed muted under
"Not applicable" in the day receipt. Reversible, persisted (`scExcludedCats`), no
data/pipeline change. A global "N categories hidden · manage" note sits below the
filter bar. **Read `docs/solutions/view-time-exclusion-and-choke-points.md`** — the
reusable lesson is that `viewDay()` is the single choke point, so this was a
one-function change. Tests + `tests/fixtures/exclude.sample.json` added.

### Possible next ideas (not committed)
- `no-store` cache header for `index.html` so code pushes show without a hard
  refresh (intentionally skipped for now).
- Net-mode Year month aggregate still uses a spend-based color heuristic (minor).

---

## Data refresh (unchanged)

Daily launchd job on Anna's Mac (9am + 4pm local, America/Denver) runs `scripts/refresh_local.sh` →
`fetch_monarch.py` (token auth) → commits `data/spending.json` → push →
Vercel redeploys. **Window = year-to-date** (Jan 1 of the current year → today), so
every month from January is populated; it resets each Jan 1. Override with
`MONARCH_START_DATE=YYYY-MM-DD` (e.g. a prior year / all history). The manual MCP
path has no window — query Jan 1 → today there to match. Manual path: Monarch MCP `get_transactions` →
`python scripts/build_from_mcp.py <dump> --today $(date +%F)`.
Full auth history + gotchas: `docs/solutions/monarch-auth-and-refresh.md`.
Note: `MONARCH_TOKEN` lives in `.env.local` (gitignored); never commit it. When
the errata strip says "Token expired", re-auth per that solution doc.

## Run / verify / deploy
```bash
npm run serve        # python http.server on :8899  → open http://localhost:8899
npm test             # Playwright smoke (zero console errors, 4 views x 2 editions)
git push origin main # auto-deploys to Vercel (direct-to-main authorized)
```

## Note
`README.md` has been refreshed to the current design (glyph verdicts, credits/net,
no-CI-cron rationale) and is no longer stale — trust it alongside this handoff and
the solution docs.

## ✅ Resolved (2026-06-03): launchd auto-refresh fixed + now twice daily
The agent had been dying with exit 126 ("Operation not permitted") — macOS TCC
blocks launchd from running a script under `~/Desktop`. Fix applied: granted Full
Disk Access to `/bin/bash`, which cleared it (`LastExitStatus = 0`, confirmed by a
launchd-triggered run that fetched + pushed on its own). The schedule was also
expanded from 9am-only to **9am + 4pm local** (America/Denver). Auto-refresh now
fires on its own — no manual step needed. Full write-up in [[monarch-auth-and-refresh]].

If it ever fails again, the first check is whether the FDA grant for `/bin/bash`
was dropped (it can reset after an OS update or if the repo moves).
