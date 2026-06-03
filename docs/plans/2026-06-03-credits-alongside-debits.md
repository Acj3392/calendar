# Plan — Credits alongside debits ("The Daily Spend")

> Phase 2 output. Brainstorm + senior review applied 2026-06-03. Read alongside
> `docs/solutions/design-tokens-and-verdict-encoding.md` (the verdict/token
> pattern this extends), `docs/solutions/smoke-test-fixed-data-blind-spots.md`,
> and `docs/HANDOFF.md`.

## Locked decisions
1. **Data shape: Option A** — each transaction keeps a **positive** `amount` and
   gains `type: "debit" | "credit"`. (Chosen over signed amounts after tracing
   the blast radius: smaller diff, row renders + validator stay ~unchanged,
   classification is explicit.) Direction is read via a single `isCredit(tx)`
   helper, never inlined.
2. **Day aggregates:** `total` (gross spend, positive) = verdict basis; add
   `received` (gross credits, positive) and `net` (`received - total`). All three
   surfaced. `received`/`net`/`type` are **optional** for backward compat
   (`type` absent → debit; `received`/`net` absent → 0).
3. **Verdict-basis toggle (Spend ↔ Net): FAST-FOLLOW PR.** Not in PR1. Net mode
   reads *net outflow* (`total - received`) and needs its own `getDateLevel`
   branch (see PR2 notes — has real edge-case bugs to handle).
4. **Credits everywhere** — distinct 4th ink (teal) + `+$` prefix, incl. credit
   category filter chips. (PR1.)

## Open decision for Anna (one, low-stakes)
Keep `EXCLUDED_CATEGORIES` (`Credit Card Payment`, `Transfer(s)`,
`Balance Adjustments`) excluded → credits = **income + refunds only**
(recommended). To count transfers-in, drop `Transfer`/`Transfers` — one-line
change. Proceeding with exclusions unless told otherwise.

---

## Architecture (static `index.html` + 2 python scripts; no DB/backend)

### Data contract (`data/spending.json`, per day)
```jsonc
{
  "date": "2026-03-04",
  "total": 205.69,        // gross SPEND (positive) — verdict basis
  "received": 1500.00,    // gross CREDITS (positive); 0 when none
  "net": 1294.31,         // received - total (positive = net inflow)
  "transactions": [
    { "merchant": "Nissan Finance", "amount": 199.89, "category": "Auto Payment", "type": "debit" },
    { "merchant": "Payroll",        "amount": 1500.00, "category": "Income",      "type": "credit" }
  ]
}
```

### Pipeline (both scripts — extract a shared helper to prevent drift)
`fetch_monarch.py` and `build_from_mcp.py` have identical per-day logic. Extract
`aggregate_by_day(transactions)` into a small shared module both import. Changes:
- Keep `EXCLUDED_CATEGORIES` (+ `hide_from_reports` in MCP script).
- **Stop dropping `amount >= 0`.** Monarch sign → `type`: `amount < 0` → debit
  (store `round(-amount,2)` positive); `amount > 0` → credit (store
  `round(amount,2)` positive, `type:"credit"`). Skip `amount == 0`.
- Per day: `total = sum(debit amounts)`, `received = sum(credit amounts)`,
  `net = round(received - total, 2)`.

### UI (`index.html`) — sign-aware in ONE atomic change
- **`isCredit(tx)`** = `tx.type === "credit"` (the only place direction is decided).
- **`viewDay(dd)`** (`:228`) — rewrite the single `reduce`: split filtered txns by
  `isCredit`; `total = round(sum debits,2)`, `received = round(sum credits,2)`,
  `net = round(received - total, 2)`. Filtering now works for debit AND credit chips.
- **`categories`** useMemo (`:218`) — split into `debitCategories` (sorted by
  spend) and `creditCategories`; sum only same-type amounts so credits don't
  distort spend ordering.
- **`validateSpending`** (`:777`) — `total` still required numeric; accept optional
  numeric `received`/`net`; if `type` present it must be `"debit"|"credit"`.
- Verdict helpers (`verdictOf`/`getDateLevel`/`cellTone`) **unchanged in PR1** —
  they keep reading `total` (spend). Net mode is PR2.

### Color (4th semantic ink — `THEMES[mode].credit` + `creditTint`)
- Teal = **money in** (additive). Never lime (=good), rust (=over), periwinkle
  (=structure). Credit amounts render `+$X` in teal, lighter weight.
- Start dark for contrast: light `credit:"#0a7268"` `creditTint:"#dcefe9"`;
  dark `credit:"#3fd9c4"` `creditTint:"#10302c"`. **Measure ≥4.5:1 both
  editions in Work (`/impeccable`)** — do not assume.
- **Net display sign convention** (used in PR1 DayDetail/Today net line): inflow
  → `+$X` teal; outflow → `−$X` muted ink (NOT rust — rust is "overspent", a
  different axis).

---

## UI/UX delivery plan (PR1)
**Journey:** Anna opens the app → spend reads exactly as before → credits called
out in teal `+$` in Today hero/ledger, DayDetail (with received + net line), small
`+` cue on calendar days with income, and credit category chips.

**Wiring matrix**
| Action | Logic | UI update |
|---|---|---|
| Load day w/ credits | `viewDay` → total/received/net | Today + DayDetail show `+$` rows + net line |
| Toggle credit chip | `viewDay` filters by category | totals/received/net + heatmap recompute |
| Day w/ income | `received > 0` | teal `+` cue on Month/Week cell |

**State matrix:** loading/error (unchanged) · no-data `—` · zero-spend `●` ·
credit-present `+$` teal · spend heatmap unchanged.

**Constraints:** ≤520px column; teal ≥4.5:1 both editions; chips keyboard-reachable.

---

## Tasks — PR1 (credits visible)

**T1 — Tracer bullet (data + all aggregation), atomic.**
Files: `scripts/aggregate.py` (new shared helper), `scripts/fetch_monarch.py`,
`scripts/build_from_mcp.py`, `tests/fixtures/spending.sample.json` (new),
`index.html` (`isCredit`, `viewDay`, `categories`, `validateSpending`).
*Done:* spend mode renders **pixel-identical** to today; `total` is still spend
(not net); category bar unchanged for debit cats; smoke green.

**T2 — Credit visual tokens + Today/DayDetail.**
`index.html`: `THEMES` teal tokens (contrast-verified); Today hero received/net
subline; ledger credit rows `+$` teal; DayDetail total + received + net header
and credit rows. *Done:* a credit day shows teal `+$` + net line both editions.

**T3 — Calendar credit cues.** Month/Week/Year: small teal `+` marker on cells
with `received > 0` (spend heatmap untouched). *Done:* income days flagged
without disturbing the good→bad spend read.

**T4 — Credit category chips.** `FilterBar` (`:566`) renders `debitCategories`
then `creditCategories`; credit chips in teal. *Done:* toggling Income recomputes
received/net.

**T5 — Tests + real data + polish.** Extend `tests/smoke.spec.js` to load the
**fixture** for credit assertions (`+$` visible, credit chip filters); keep the
live-data load for the existing zero-error sweep. Regenerate real
`data/spending.json` via live refresh. `/impeccable` pass on teal.
*Done:* `npm test` green, screenshots clean both editions.

> **Op note:** pause the 9am MST launchd cron during dev so it can't overwrite the
> working tree; the fixture-based test makes credit assertions independent of the
> rolling 90-day window regardless.

## Tasks — PR2 (net-verdict toggle, fast-follow)
- `metricOf(dd)`: spend → `total`; net → `total - received` (net outflow).
- **Dedicated net `getDateLevel` branch** — fixes two real bugs: (a) empty day
  (`metric===0`) must NOT read "Net positive"; gain requires
  `received > 0 && netOutflow <= 0`. (b) pure-income day (`total===0`,
  `received>0`) must read net-positive, not "No spend ●".
- New level `"gain"` → `verdictOf` `{tone:"good", label:"Net positive ✦"}`,
  `cellTone` good wash. Reuse existing thresholds on net outflow (no new sliders).
- Settings segmented control (Spend/Net), persisted `localStorage` key
  `scVerdictBasis` (default **spend**); legend gains "Net positive".
- **Always-visible mode indicator** when net is active (don't rely on legend).
- Tests: explicit cases for empty / pure-income / refund-offsets-spend days.

## Test strategy
- **Smoke (Playwright):** zero console errors, 4 views × 2 editions (existing) +
  fixture-backed credit `+$` + credit chip (PR1) + net-toggle edge cases (PR2).
- **Python:** doctest/tiny assert on `aggregate_by_day` (one helper, two callers).
- **Manual:** live Monarch refresh yields valid Option-A JSON.

## Ready for: Work Phase — start at PR1 / T1.
