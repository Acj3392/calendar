# Plan: Focus highlights only category-spend days

> Date: 2026-06-03 · Feature slug: `focus-only-spend-days`
> Scope: `index.html` only (single static file, no build/backend/DB) + a new test
> fixture. Follows [[filtered-verdict-needs-own-basis]] (Focus mode).

---

## Problem (grounded in code + the May screenshot)

In Focus mode the lime "good / met goal" wash leaks onto days with **zero category
spend**, so the highlight no longer means "I spent on this here." Two leaks, both
in `getDateLevel` (index.html:324):

1. **Empty in-range days** (May 28 — no transactions at all). The early
   `if (!dd) return inRange ? "zero" : "none"` (line 328) runs *before* the Focus
   guard, so a no-record day returns `"zero"` → `cellTone("zero")` = lime
   `goodTint`.
2. **Credit-only category days** (May 16 `+$77`, May 22 `+$166` — refunds in the
   category). The Focus guard requires `received === 0` (line 331), so a
   refund-only day falls through to `if (dd.total === 0) return "zero"` → lime.

Net effect: no-spend days light up the same green as real spend days, and the
filtered view stops answering "which days did I spend on this?"

## Decision (confirmed with user)

- **Focus fill = category spend only.** A day gets a verdict fill (lime under-avg /
  neutral on-pace / rust over) **iff it has category spend (`dd.total > 0`)**.
- **Every zero-category-spend day recedes** as `"absent"` — empty, out-of-category,
  or credit-only alike.
- **Credit-only days recede but keep a faint teal `+` marker** (already rendered
  independently when `dd.received > 0`), so money-back is still visible without a
  "good day" wash. No dollar figure on these — just the `·` + `+`.
- Applies in **both Spend and Net basis** for consistency (a filtered credit-only
  day no longer reads as ✦ "net positive"; it recedes).

## Architecture (frontend-only)

Restructure `getDateLevel` so the Focus branch is evaluated **first and as a
whole**, instead of the current empty-day early-return preceding the Focus guard:

```js
const getDateLevel = (ds) => {
  const raw = spendingMap[ds];
  const dd  = viewDay(raw);
  const inRange = ds >= MIN_DATE && ds <= TODAY;

  // Focus mode: only days with category SPEND get a verdict fill; empty,
  // out-of-category, and credit-only days all recede as "absent".
  if (isFiltered) {
    if (!dd || dd.total === 0) return (!raw && !inRange) ? "none" : "absent";
    if (netMode) {
      const outflow = Math.round((dd.total - dd.received) * 100) / 100;
      if (dd.received > 0 && outflow <= 0) return "gain";
      return getLevel(outflow);
    }
    return getLevel(dd.total);
  }

  // Unfiltered — unchanged.
  if (!dd) return inRange ? "zero" : "none";
  if (netMode) { /* …existing… */ }
  if (dd.total === 0) return inRange ? "zero" : "none";
  return getLevel(dd.total);
};
```

No change to `cellTone` (`"absent"` already = transparent + faint), `verdictOf`
(`"absent"` → "No {category}"), or the `+`-badge logic in Month/Week. The fix is
purely *which days resolve to `"absent"`*.

## UI/UX Delivery Plan

- **Journey:** Anna filters a category → only the days she actually spent on it
  carry a fill (lime under her per-category average, rust over); every other day —
  empty, other-category, or refund-only — recedes to a faint `·` (refund days also
  show a small teal `+`). The "which days" answer is now unambiguous.
- **State matrix (filtered):**
  | Day | Resolves to | Renders |
  |---|---|---|
  | Category spend ≤ low | `low`/`gain` | lime fill, ✓/✦ + amount (figure) |
  | Category spend mid/high | `medium`/`high` | neutral / rust fill + amount |
  | Other-category spend only | `absent` | faint `·`, no fill |
  | Refund-only in category | `absent` | faint `·` + teal `+`, no fill |
  | Empty in-range day | `absent` | faint `·`, no fill |
  | Out-of-range day | `none` | blank |
- **UX constraints:** colorblind glyphs intact; lime stays fill-only; Day/Night
  parity; no layout shift.

## Tasks (in order)

1. **Recede every zero-spend day in Focus mode**
   `index.html` — restructure `getDateLevel` (Focus branch first). Verify the `+`
   badge still shows for credit-only days in Month/Week and DayDetail of an absent
   day reads "No {category}".
   *Outcome:* filtered grid fills only category-spend days; May 28 and refund-only
   days recede.

2. **Deterministic fixture for the recede cases**
   New `tests/fixtures/focus.sample.json` (separate from `spending.sample.json` so
   the existing net-decomp assertions keep their numbers). Includes: a low spend
   day, a high spend day, an other-category day, a refund-only-in-category day, and
   an empty in-range day.

3. **Smoke test: Focus fills spend days only**
   `tests/smoke.spec.js` — route the focus fixture, filter the category, then assert
   via computed `background`: a spend day's cell is filled (non-transparent) while
   the refund-only day and the empty in-range day are transparent (receded). Assert
   the refund day still shows its `+`. Zero console errors.

## Test Strategy

- **Unit-ish (in fixture):** `getDateLevel` returns `"absent"` for empty/
  credit-only/other-category days when filtered, and a tiered level only when
  `dd.total > 0`.
- **E2E (Playwright):** computed-style assertion that receded days have transparent
  backgrounds and spend days don't; refund day retains `+`; runs without console
  errors. Per [[smoke-test-fixed-data-blind-spots]], use the routed fixture, not
  the live window.
- **Regression:** existing 5 smoke tests must stay green (unfiltered behavior and
  net-decomp numbers untouched).

## Ready for: Work Phase
