# Plan: Make active filtering visually dominant ("Focus mode")

> Date: 2026-06-03 · Feature slug: `filtered-mode-emphasis`
> Scope: `index.html` only (single static file, React via CDN, no build/backend/DB).
> Source brief: make category filtering reframe the calendar around "how much did I
> spend on *this*, and on which days" — without hiding the no-spend days.

---

## Problem (grounded in code)

When `activeCats.length > 0`:
- `viewDay()` (index.html:274) recomputes each day's `total` from only the
  filtered transactions. Good — figures are already correct.
- **But verdict tiers stay global.** `getLevel()` (index.html:284) compares the
  filtered total against the global `$75 / $300` thresholds. A heavy grocery day
  ($90) and a heavy *overall* day are judged on the same scale, so green/red is
  meaningless for a single category.
- **No-spend-in-category days disappear into "zero".** A day that had $400 of
  other spending but $0 of groceries returns `total:0, received:0` →
  `getDateLevel` returns `"zero"` → renders as "A clean day ●" (index.html:300,
  628). It looks identical to a genuinely empty day **and** sits at the same
  visual weight as days that *did* have groceries. Filtering does nothing to make
  the spend days pop.

So the fix is two things: **(1) re-scope the verdict to the filtered slice**, and
**(2) introduce a "Focus mode" visual treatment** that pushes has-spend days
forward and lets no-spend days recede (but stay visible).

---

## Two load-bearing decisions (recommended defaults baked in — confirm)

1. **Where do filtered thresholds come from?**
   **Recommended:** derive them from the filtered category's *own* distribution in
   the loaded window. Compute the mean daily spend across days where the filtered
   set appears (`catAvg`); set `low ≤ 0.6 × catAvg`, `high ≥ 1.4 × catAvg`. Label
   it in the UI ("vs your groceries average"). This makes ✓/▲ mean "light vs heavy
   grocery day *for you*" with zero manual config, and degrades gracefully for any
   category. (Alternative considered: manual per-category targets — more accurate,
   but needs a data model + settings UI; defer.)

2. **Multi-category filter behavior?**
   **Recommended:** treat it as one combined slice. Thresholds derive from the
   combined set's distribution; header reads "3 categories". Verdict answers "did I
   overspend across this group." (Simplest, consistent with how `viewDay` already
   unions categories.)

---

## Architecture

- **Database / API / AI:** none. Pure client render logic in `index.html`.
- **New derived state:** `isFiltered = activeCats.length > 0` (memoized).
- **New helper `filteredThresholds()`** (memoized over `RAW_DATA` + `activeCats`):
  returns `{ low, high, catAvg }` from the filtered category's distribution.
  Falls back to global thresholds when `!isFiltered`.
- **`getLevel()` / `getDateLevel()` updated** to use `filteredThresholds()` when
  filtered, and to introduce a new level for the figure/ground split:
  - `"focus-spend"` adjacency is *not* a new tier — keep `low/medium/high` for the
    verdict color. Instead add a **separate boolean per cell**: `hasCatSpend`
    (the day had ≥1 transaction in the filtered set). Days where `hasCatSpend` is
    false but the day *did* exist render as the recede state.
- **`cellTone()` (index.html:322) unchanged** for color semantics; the Focus
  treatment layers *emphasis* (weight, size, dimming) on top, so colorblind glyphs
  and lime/rust meaning are preserved.

### Focus-mode visual contract (the designer's job)
- **Header reframe:** masthead/section head shows the filtered category + its
  total as the headline (e.g. "Groceries · The Month — $312"), replacing
  "The Month in Full". The existing `Filtered · N categories · tap All to clear`
  strip (index.html:756) stays but is promoted, not a footnote.
- **Has-spend days (figure):** full ink, verdict fill as today, the verdict glyph
  + amount at normal/slightly-larger size. These are the answer to "which days."
- **No-spend-in-category days (ground):** still rendered in the grid, but quieted —
  no fill, faint hairline, a low-contrast "·" (distinct from the genuine-empty
  `—`). Reads as "no groceries this day," not "clean day."
- **Genuinely empty days** keep their existing out-of-range `—` / `none` look.
- Transition into/out of filtered state should feel deliberate (a subtle fill
  fade is enough — no heavy animation; respect no-build constraints).

---

## UI/UX Delivery Plan

- **User journey:** Anna taps a category chip (e.g. Groceries) in any view →
  the view visibly shifts into Focus mode → spend days pop, no-spend days recede,
  verdict colors now answer "heavy/light grocery day" → taps **All** to exit.
- **Wiring matrix:**
  | Action | Logic path | UI result |
  |---|---|---|
  | Tap category chip | `setActiveCats` → `isFiltered=true` → `filteredThresholds()` recompute | Header reframes; cells split figure/ground; verdict re-scoped |
  | Tap second chip | combined slice | thresholds re-derive; header → "N categories" |
  | Tap **All** | `setActiveCats([])` | returns to unfiltered budget verdict + normal weighting |
  | Spend/Net toggle while filtered | existing `basisAmount` path | figures + headline respect net basis on the filtered slice |
- **State matrix:** unfiltered (today's look) · filtered-with-spend (figure) ·
  filtered-no-spend (ground) · empty/out-of-range (`—`) · category total = 0 in
  window (edge: avoid divide-by-zero in `catAvg`, fall back to global thresholds).
- **UX constraints:** colorblind-safe glyphs intact; lime stays fill-only;
  Day/Night editions both styled; mobile chip row + grid unchanged in layout.

---

## Tasks (in order)

1. **Filtered thresholds helper + edge handling**
   `index.html` (add `filteredThresholds()` memo near line ~274; guard
   `catAvg === 0`). Wire `getLevel`/`getDateLevel` to use it when `isFiltered`.
   *Test:* unit-style assertion in smoke fixture — a known grocery day tiers
   `high` against category avg, not global. *Outcome:* verdict color reflects the
   category, invisibly (no UI change yet) — verify via cell color in a filtered
   screenshot.

2. **`hasCatSpend` figure/ground split in MonthView**
   `index.html` MonthView cells (594–632): compute `hasCatSpend`; render figure vs
   recede vs empty as three distinct states. *Test:* smoke — filter to a category,
   assert a no-spend day shows the recede marker (not "●" clean), and a spend day
   shows the amount + glyph. *Outcome:* month view visibly reframes on filter.

3. **Header reframe + promoted filtered strip**
   `index.html` MonthView header (636–637) + FilterBar strip (756). Category name
   + filtered total as headline; "N categories" wording. *Test:* smoke asserts
   header text contains the active category when filtered. *Outcome:* unmistakable
   "you are filtered" signal.

4. **Propagate Focus mode to Today / Week / Year**
   `index.html` TodayView (~480), WeekView (~542), YearView (~651): same
   figure/ground + re-scoped verdict + reframed headline. *Test:* smoke loops all
   views × both editions with a filter active, zero console errors, spend vs
   no-spend distinguishable. *Outcome:* applies to the whole app, every view.

5. **Polish pass (designer review) + Day/Night parity**
   Tune weights/dim levels, transition, contrast in both `THEMES`. Verify
   `docs/solutions/design-tokens-and-verdict-encoding.md` + `no-build-theming`
   patterns honored. *Outcome:* ships at design bar, both editions.

---

## Test Strategy

- **Unit (in-page logic via fixture):** `filteredThresholds()` math —
  correct `low/high/catAvg`; `catAvg=0` falls back to global; multi-category
  combines. Use `tests/fixtures/spending.sample.json` (route a deterministic
  grocery distribution in).
- **Integration / E2E (Playwright, `tests/smoke.spec.js`):**
  - Filter active → no-spend day renders recede marker, not "clean ●".
  - Filter active → spend day shows amount + verdict glyph at figure weight.
  - Header reframes to the category + total.
  - All views × Day/Night editions render filtered with **zero console errors**.
  - Tapping **All** restores unfiltered verdict + weighting.
- **Smoke blind-spot guard:** per
  `docs/solutions/smoke-test-fixed-data-blind-spots.md`, route the filtered
  fixture explicitly rather than asserting against the live window.

---

## Ready for: Work Phase
Open the two recommended decisions for confirmation, then run
`campco-product:workflow-work` from Task 1.
