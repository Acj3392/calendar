---
title: "Credits alongside debits: data shape, net-spent framing, and the Spend/Net basis"
date: 2026-06-03
tags: [ui, data, finance, design]
category: pattern
module: ui
symptoms: ["credits inflate spend totals", "net shows a confusing −$893", "should the headline be gross or net", "income/refund days look like spending"]
---

# Credits alongside debits

Context: `index.html` was spend-only (both pipeline scripts dropped `amount >= 0`
inflows). This added credits (income, refunds) end to end. Builds on
[[design-tokens-and-verdict-encoding]] and [[no-build-theming-and-chrome]].

## Problem

Three decisions shaped everything, and two of them were non-obvious enough that
the first instinct was wrong:

1. **Data shape.** Signed amounts (Monarch-native) *felt* cleaner but the blast
   radius was large: every `sum(amount)` site (`viewDay`, `categories`, every
   `wTotal/mTotal/yTotal`) silently flips from "spend" to "net" the moment data
   is signed, and every row render needs a sign branch — all for no real payoff,
   since the day aggregates are recomputed as positive magnitudes anyway.
2. **What is "net".** Displaying `net = received − total` made a normal spending
   day read as a negative "**−$893**", which reads as wrong in a spending app.
3. **Gross vs net headline.** Users expect money-in to *offset* the day's cost.

## Solution

### Option A data shape (positive amount + explicit `type`)
Each transaction keeps a **positive** `amount` plus `type: "debit" | "credit"`.
Days gain `received` (gross credits) and `net` (`received − total`), both
optional for backward-compat (`type` absent → debit; `received`/`net` absent → 0).
`total` stays **gross spend**. This kept `validateSpending`, the row renders, and
the verdict/heatmap essentially unchanged. Direction is read through one helper,
never inlined: `const isCredit = (tx) => tx.type === "credit";`

A shared `scripts/aggregate.py` (`aggregate_by_day`) is imported by both
`fetch_monarch.py` and `build_from_mcp.py` so the two pipelines can't drift; it
tags `type` from Monarch's sign and stores positive magnitudes.

### Credit chips list credit-ONLY categories
Splitting categories by type naively double-listed the ~16 categories that have
both debits and credits (refunds land in normal spend categories). Worse, since
filtering is by **category name**, the debit chip and the teal credit chip
returned the identical set. Fix: `creditCategories` excludes anything already in
`debitCategories` (21 → 5 income-only chips against live data).

### "Net spent" framing, not signed net
Display net as `total − received` (net **spent**), not `received − total`:
- net outflow → plain positive `$893` (it's still spending, no minus)
- net inflow → `+$X` in teal (the day came out ahead)

This killed the confusing `−$893`. The receipt now reconciles top-to-bottom:
`Total Spent − Total Received = Net`.

### The Spend/Net basis is a display+verdict toggle, applied everywhere
A persisted `verdictBasis` (`scVerdictBasis`, default `spend`) drives a single
`basisAmount(dd)`:
```js
const basisAmount = (dd) => netMode ? round2(dd.total - dd.received) : dd.total;
```
In **Net mode** this is the headline AND every cell/period number (money-in
offsets the day); in **Spend mode** it's gross. Threading it through one helper
(+ `fmtAmt` which renders net-gain as `+$` teal) kept Spend mode — the default —
byte-for-byte unchanged, so all existing tests stayed green.

Net-mode `getDateLevel` needs its **own branch**, not just a metric swap, to avoid
two bugs: an empty day (`total===0 && received===0`) must stay `zero` (not a false
"Net positive"), and a pure-income day (`total===0, received>0`) must read the new
`gain` tier (not "No spend"). `gain` only when `received > 0 && netOutflow <= 0`.

## Why It Works

Keeping `total` = gross spend as the invariant meant the risky logic (verdict,
tones, levels) never changed shape; credits are a strictly additive layer.
Routing the gross-vs-net choice through `basisAmount`/`fmtAmt`/`netSpentParts`
means a view never decides the basis — it asks a helper — so Spend mode is
provably unchanged and Net mode is a one-line metric difference.

## Related
- [[design-tokens-and-verdict-encoding]] — verdict/`mark` glyph + tint system (extended here)
- [[smoke-test-fixed-data-blind-spots]] — why the credit-chip dup hid (fixture had no overlapping category)
- [[css-grid-1fr-overflow]] — the Net-mode wide-number grid overflow
- `docs/plans/2026-06-03-credits-alongside-debits.md` — the plan (shipped)
- `index.html` — `isCredit`, `sumTxns`, `basisAmount`, `fmtAmt`, `netSpentParts`, `verdictOf`, `Receipt`
