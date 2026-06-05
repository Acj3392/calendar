---
title: "View-time category exclusion via the viewDay choke point"
date: 2026-06-05
tags: [ui, architecture, state, testing]
category: pattern
module: ui
symptoms: ["need to hide a category from every total/verdict", "a cross-cutting view change touches many components", "totals and a detail list must disagree on purpose"]
---

# View-time category exclusion via the viewDay choke point

## Problem

Add user-toggleable "not applicable" categories (e.g. Mortgage) that vanish from
every total / net / verdict across Today / Week / Month / Year — in BOTH directions
(the payment out AND any money in) — while still being listed (muted) in the day's
receipt. A naive read of the app suggests a sprawling change: four view components,
the heatmap, the day detail, the month/year rollups, the filter chips.

## Solution

It was a one-function change because **`viewDay(dd)` is the single choke point**.
Every view headline and `getDateLevel()` verdict computes its figures by calling
`viewDay` → `sumTxns`. Verified, don't assume — confirm with grep before relying on
it:

```
TodayView:528, WeekView:599, MonthView:540/662, YearView:729  → all viewDay→basisAmount
```

The only direct `RAW_DATA` reads were `spendingMap` (lookup), the category-chip
sums, and `filteredThresholds` (focus-only). None compute display totals. So:

```js
const isExcluded = (tx) => excludedCats.includes(tx.category);
const viewDay = (dd) => {
  if (!dd) return null;
  const txns = activeCats.length
    ? dd.transactions.filter(tx => activeCats.includes(tx.category))
    : dd.transactions;
  const counted = txns.filter(tx => !isExcluded(tx));   // <- the whole feature
  return { ...dd, transactions: txns, ...sumTxns(counted) };
};
```

Three patterns made the rest fall out cleanly:

1. **Keep the data, change the count.** `.transactions` still carries excluded txns
   (so the Receipt can show them muted under "Not applicable"); only `total/received/net`
   are computed from `counted`. "Hidden but still listed" = the array and the sum
   disagree on purpose.

2. **Two lists: manage vs. display.** `allCategories` (every category, both
   directions) feeds the Settings hide-toggle so you can *un-hide* — including
   credit-only categories. The filter-chip lists are `*All.filter(!excluded)` so a
   hidden category can't be focused. Don't reuse one list for both jobs.

3. **Direction-blind by name = net stays clean for free.** Excluding by category
   name drops the debit and the credit together, so net is unaffected by a hidden
   category in either direction — no special-casing.

Persistence mirrors the other prefs (`scTheme`, `scVerdictBasis`) but is the first
*array*-shaped one, so the parse is defensive: `Array.isArray` + per-element
`typeof` guard, falling back to `[]`. A stale name (category gone after a refresh)
matches nothing and self-heals. `toggleExcluded` also drops the category from
`activeCats` (you can't focus what you're hiding).

## Why It Works

A choke point is leverage: when one function is the sole producer of the value every
consumer reads, a cross-cutting change to that value is a one-line edit, not an
N-component sweep. The risk is assuming the choke point holds — so the discipline is
to *verify by grep* that no consumer bypasses it (here, that no view summed
`RAW_DATA` directly). The one genuinely separate code path was the Receipt's
`received === 0` flat-list early return — the predictable place a "handle it
everywhere" change forgets, so it got its own test.

## Related
- `docs/solutions/credits-and-net-basis.md` — establishes `viewDay`/`sumTxns` and the net basis this builds on
- `docs/solutions/filtered-verdict-needs-own-basis.md` — focus mode, which exclusion sits beneath
- `docs/solutions/smoke-test-fixed-data-blind-spots.md` — why this used a dedicated `exclude.sample.json` fixture
- Plan: `docs/plans/2026-06-05-not-applicable-categories.md`
