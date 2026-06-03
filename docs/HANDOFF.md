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

## ▶ NEXT UP: add credits alongside debits

Today the app is **spend-only**: both pipeline scripts drop every inflow and the
UI assumes positive outflow. The next task is to bring **credits (income,
refunds, transfers in)** into the picture.

### The exact code that excludes credits
Both scripts keep only `amount < 0` (Monarch convention: outflows negative) and
store the absolute value as a positive `amount`:
- `scripts/fetch_monarch.py` ~line 92-96 (`if amount >= 0: continue`)
- `scripts/build_from_mcp.py` ~line 51-55 (`if amount is None or amount >= 0: continue`)

### Decisions to make first (these shape everything downstream)
1. **Data shape.** Keep `amount` positive + add a `type: "debit" | "credit"` (or
   `direction`) per transaction? Or switch to **signed** amounts? Recommend
   `type` + positive `amount` (least churn to `validateSpending` and existing
   render code; explicit). Whatever you pick, update `validateSpending()` in
   `index.html` to accept it (it currently requires `total` number +
   `transactions[]` with numeric `amount`).
2. **What is a day's `total`?** Options: keep `total` = gross spend (debits) and
   add a separate `received`/`credits` field; OR a `net`. Recommend keeping
   `total` = spend (so the verdict/heatmap stay meaningful) and adding
   `received` alongside — don't let credits silently change the "overspent"
   reading.
3. **Verdict semantics.** "Overspent / met goal" is about *spending*. Decide if
   credits affect the verdict (probably not — keep verdict on debits, show
   credits as a separate positive signal).

### UI surfaces that assume spend-only (all in `index.html`)
- `viewDay()` — filters/sums `transactions`; will need to respect debit/credit.
- `cellTone()` / `verdictOf()` / `getDateLevel()` — driven by spend `total`.
- **TodayView** hero + "Today's Ledger" rows · **DayDetail** rows + total ·
  **Month/Week/Year** cell amounts + section totals.
- **FilterBar** — categories derived from `transactions`; credits add new ones.
- Likely want a **visual language for credits** (e.g. a `+$X` in a calm
  positive treatment — careful: acid-lime is already "met goal", green could
  read as that; consider a distinct ink or a `+` prefix + lighter weight).

### Suggested flow
Run the loop: `/workflow-brainstorm` (lock the 3 decisions above) →
`/workflow-plan` → `/workflow-work` (start with the two Python scripts + a
hand-edited `data/spending.json` sample so you can build the UI before a live
refresh) → `/workflow-review` → `/workflow-compound`. Apply `/impeccable` for the
credit visual language. Verify with the Playwright smoke + browser screenshots in
both editions.

---

## Data refresh (unchanged)

Daily launchd job on Anna's Mac (9am MST) runs `scripts/refresh_local.sh` →
`fetch_monarch.py` (token auth) → commits `data/spending.json` → push →
Vercel redeploys. Manual path: Monarch MCP `get_transactions` →
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
`README.md` is pre-redesign (mentions emoji markers, a 6h cron) and is stale on
the UI; trust this handoff + the solution docs. Worth refreshing the README at
some point, but it's not load-bearing.
