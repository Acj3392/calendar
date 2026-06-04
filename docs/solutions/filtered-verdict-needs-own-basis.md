---
title: "A category filter needs its own verdict basis (Focus mode)"
date: 2026-06-03
tags: [ui, filtering, verdict, ux]
category: pattern
module: ui
symptoms: ["filtering a category doesn't visually reframe the view", "per-category green/red is meaningless", "no-spend days look identical to clean days when filtered", "filtered state isn't obvious"]
---

# A category filter needs its own verdict basis (Focus mode)

Context: `index.html` (the whole app, React via CDN, no build). Category filtering
already recomputed each day's figures via `viewDay()` — but the *verdict* and the
*visual treatment* still answered the unfiltered question, so filtering did almost
nothing perceptible. Builds on [[design-tokens-and-verdict-encoding]] and
[[credits-and-net-basis]].

## Problem

When a category was selected, the filter changes the **question** — from "how was
my day overall?" to "how much went to *this*, and on which days?" — but two things
didn't follow:

1. **Verdict judged on the wrong scale.** `getLevel()` tiered the filtered total
   against the **global** `$75 / $300` thresholds. A $90 grocery day was judged
   like a $90 total day, so met-goal/over (lime/rust) was noise for a single
   category.
2. **No-spend-in-category days masqueraded as "clean."** A day with $400 of *other*
   spending but $0 of groceries returns `total: 0` → fell into the `"zero"` level →
   rendered as "A clean day ●", visually identical to a genuinely empty day **and**
   at the same weight as days that *did* have groceries. Nothing stood out.

So the numbers were right and the experience was wrong.

## Solution

Two moves, both keyed off `isFiltered = activeCats.length > 0`.

### 1. Re-scope the verdict to the slice's own distribution
Derive thresholds from the filtered category's own daily average across the loaded
window — no per-category config, no data model:
```js
const filteredThresholds = useMemo(() => {
  if (!activeCats.length) return null;
  let sum = 0, days = 0;
  RAW_DATA.forEach(d => {
    const tot = d.transactions.reduce((s,tx) =>
      (!isCredit(tx) && activeCats.includes(tx.category)) ? s + tx.amount : s, 0);
    if (tot > 0) { sum += tot; days++; }
  });
  if (days === 0) return null;           // empty slice → fall back to global
  const avg = sum / days;
  return { low: avg * 0.6, high: avg * 1.4, avg };
}, [activeCats]);
```
`getLevel()` reads `filteredThresholds` when present, else the global thresholds.
So ✓ / – / ▲ now mean "light / typical / heavy *for this category*". Multi-category
= one combined slice (thresholds derive from the union). The strip surfaces the
basis: `judged vs $115/day avg`.

### 2. A distinct "absent" level for figure/ground
Days that exist and had activity, but nothing in the active slice, get their own
level so they recede instead of reading as a clean day:
```js
if (isFiltered && dd.total === 0 && dd.received === 0) {
  return raw.transactions.length ? "absent" : (inRange ? "zero" : "none");
}
```
`"absent"` renders as a faint `·` (vs `●` clean, vs `—` empty) with `textFaint`
ink and no fill. Spend days keep full weight + verdict fill + glyph + amount → they
become the figure, absent days the ground, and every day still shows on the grid.

### 3. Make the filtered state unmistakable
A lime **FOCUS · {category}** pill + derived-avg context, and each view's header
reframes (`Groceries · The Month`, `Coffee Shops · 2026`, `Groceries today`). The
verdict applies in all four views (Today/Week/Month/Year) and the Year view's
monthly tier also re-scopes to the filtered thresholds.

## Gotchas / lessons

- **Recompute the figures *and* the basis.** A filter that re-sums but keeps the
  old judgment scale looks broken in a subtle way — the numbers move, the colors
  lie. Whenever a view re-scopes *what* it measures, re-scope *how it judges* too.
- **`viewDay()` returns a truthy day object even when the filtered slice is empty**
  (`total: 0`). Check the *raw* record's transaction count, not `dd`, to tell
  "no spend in this category" apart from "nothing happened that day."
- **Guard the divide-by-zero.** A filtered category with zero in-window spend ⇒
  `days === 0`; return `null` and fall back to global thresholds rather than `NaN`.
- **Don't add a redundant clear control.** A dedicated "Clear" button competed with
  the existing **All** chip and got pinned to the edge where it clipped. The All
  chip + "tap All to clear" hint is enough.

## Where
- `index.html`: `filteredThresholds`, `getLevel`, `getDateLevel` (`"absent"`),
  `verdictOf`/`cellTone` (`"absent"`), `FilterBar` strip, all four view headers.
- Test: `tests/smoke.spec.js` — "filtering engages Focus mode".
- Plan: `docs/plans/2026-06-03-filtered-mode-emphasis.md`.
