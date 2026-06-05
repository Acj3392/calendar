# Plan: "Not applicable" categories (user-hidden from totals)

> Date: 2026-06-05 · Feature slug: not-applicable-categories
> Brainstorm decisions: hide from totals but still list muted in day detail ·
> manage in Settings gear popover · subtle "N hidden" reminder · exclude by
> category name in BOTH directions (debit + credit).

## Problem

Some categories (e.g. mortgage in *and* out) aren't controllable spending, so
their numbers are noise. Anna wants to mark categories "not applicable" so they
drop out of every total / net / verdict across Today / Week / Month / Year, while
still being visible (muted) in the day's receipt — and reversible at any time.

## Architecture

- **No backend / DB / API / AI.** Static `index.html`, same as the rest of the app.
- **Data model = one localStorage key:** `scExcludedCats` → JSON array of category
  name strings. Default `[]`. Mirrors the existing `scTheme` / `scVerdictBasis`
  prefs pattern (lines 178–192). `spending.json` is untouched — exclusion is a
  pure view-time concern, so the choice is instant and reversible with no refresh.
- **Single choke point (VERIFIED, not assumed):** `viewDay()` (index.html:301–307)
  feeds every headline total and `getDateLevel()` verdict. Confirmed every view
  routes through it: TodayView:528, WeekView:599, MonthView:540/544 & 662/669,
  YearView:729 — all `viewDay(...)` → `basisAmount`. The only direct `RAW_DATA`
  reads are `spendingMap` (230), the category lists (246), and `filteredThresholds`
  (277) — none compute display totals, and `filteredThresholds` is focus-only
  (excluded categories can't be focused). So computing `total/received/net` from the
  *non-excluded* subset in `viewDay` propagates to all four views + verdicts for free.

### Terminology (keep consistent)
User-facing word is **"Hidden"** (Settings: "Hide categories"; receipt header:
"Not applicable"). Internal identifier is `excluded` / `excludedCats`. Don't let
the UI label drift into a second vocabulary.

### Compounded-knowledge constraints (from docs/solutions/)
- `credits-and-net-basis.md`: excluding a category must drop **both** its debit and
  credit so net stays clean. → `isExcluded(tx)` is by category name, direction-blind. ✓ (free)
- `filtered-verdict-needs-own-basis.md`: `filteredThresholds` (274–285) reads raw
  transactions for the *focused* category. Excluded categories are removed from the
  FilterBar chips, so they can never be the focused slice → no change needed there,
  but `toggleExcluded` should defensively also drop the category from `activeCats`.

## Key design points

1. **`viewDay` keeps all transactions, counts only non-excluded ones:**
   ```js
   const isExcluded = (tx) => excludedCats.includes(tx.category);
   const viewDay = (dd) => {
     if (!dd) return null;
     const txns = activeCats.length
       ? dd.transactions.filter(tx => activeCats.includes(tx.category))
       : dd.transactions;
     const counted = txns.filter(tx => !isExcluded(tx));
     return { ...dd, transactions: txns, ...sumTxns(counted) };
   };
   ```
   `total/received/net` now skip excluded; `.transactions` still carries them so the
   Receipt can render them muted. (No `hasExcluded` field — nothing consumes it; the
   HiddenNote keys off global `excludedCats.length` and the Receipt re-partitions
   `dd.transactions` itself.)

   **Defensive persistence:** `scExcludedCats` is the first *array*-shaped pref, so the
   init must guard the parse — `try { const a = JSON.parse(...); return Array.isArray(a)
   ? a.filter(x => typeof x === "string") : []; } catch { return []; }`. A stale name
   (category gone after a refresh) matches nothing and self-heals — no need to validate
   against known categories. `toggleExcluded(c)` writes localStorage AND drops `c` from
   `activeCats` (defensive: you can't focus a category you're hiding).

2. **Two category lists, not one:**
   - `allCategories` (new memo) — every category name in the data, both directions →
     feeds the Settings toggle list (so you can un-hide).
   - `debitCategories` / `creditCategories` (244–257) — add
     `.filter(c => !excludedCats.includes(c))` so hidden categories vanish from the
     FilterBar chips.

3. **Receipt (435+) gains a muted "— Not applicable —" section.** Partition
   `dd.transactions` into counted debits, counted credits, and excluded (either
   direction). Render counted in the existing Spending / Money-in sections; render
   excluded under a faint section that does not affect the subtotals (which already
   exclude them via `viewDay`). The `dd.received === 0` flat-list early return must
   also split out excluded rows.

4. **"N categories hidden" reminder** — a single shared `<HiddenNote/>` (tappable →
   `setShowSettings(true)`), shown when `excludedCats.length > 0`, rendered **once** in
   the shell right after `<FilterBar/>` (line 982). One placement, not four per-view
   copies: it sits directly above all views, reads as "these numbers exclude N
   categories," and has no duplication to drift or re-test.

5. **Settings "Hide categories" section** — new block in the popover after
   Thresholds (index.html:958, before the legend). Scrollable list (max-height
   ~150px, overflow auto) of `allCategories`; each row a toggle with a check/✓ when
   hidden; header shows the count. `toggleExcluded(c)` writes localStorage and
   removes `c` from `activeCats`.

## UI/UX Delivery Plan

- **User journey:** Anna opens the gear → "Hide categories" → toggles Mortgage on →
  every total/verdict drops Mortgage instantly → a "1 category hidden" note appears
  near totals → opening any day still shows the Mortgage line, muted, under "Not
  applicable" → toggling it off restores everything.
- **Wiring matrix:**
  | Action | State change | UI update |
  |---|---|---|
  | Toggle category in Settings | `excludedCats` ± name → localStorage; drop from `activeCats` | all totals/verdicts recompute; chip hides; HiddenNote count updates; receipt re-partitions |
  | Tap HiddenNote | `setShowSettings(true)` | popover opens to manage hidden set |
  | Reload page | read `scExcludedCats` | exclusions persist |
- **State matrix:** empty (none hidden → no note, no muted section, identical to
  today) · active (≥1 hidden → note + muted section) · all-in-category-hidden day
  (counted total 0 but day still listed) · focused-then-hidden (category cleared
  from focus).
- **UX constraints:** toggles `aria-pressed`; list keyboard-focusable; HiddenNote a
  real `<button>`; muted section meets contrast via `t.textFaint`; chip row + list
  scroll on mobile (existing `no-scrollbar` pattern).

## Tasks (in order) — revised per senior review

1. **Core math + Settings toggle (first usable slice)** — `index.html`: state ~177
   (`excludedCats` w/ defensive array parse), `isExcluded`, `toggleExcluded` (writes
   localStorage + drops from `activeCats`), `allCategories` memo, `debit/creditCategories`
   filter to drop hidden chips, and the **"Hide categories"** popover section (~958).
   `viewDay` (301–307) counts only non-excluded. *E2E: toggle a category in Settings →
   Month/Today totals drop by the known amount; toggle off → restores; persists across
   reload.* Outcome: Anna can hide/un-hide a category and watch every total move.
   (Merged former Tasks 1+2 — math alone wasn't user-operable, violating vertical-slice.)

2. **Receipt "Not applicable" section** — `index.html` `Receipt` (435+, BOTH the
   `received === 0` flat path AND the split path) — *E2E: day detail lists the hidden
   txn muted under "Not applicable"; subtotal excludes it.* Outcome: hidden
   transactions stay visible but uncounted.

3. **Single global HiddenNote** — `index.html` once after `<FilterBar/>` (982) —
   *E2E: note shows "1 category hidden" and opens Settings on tap; gone when none
   hidden.* Outcome: the user is reminded numbers are partial.

4. **Test fixture + smoke assertions** — `tests/fixtures/spending.sample.json`
   (ensure a clearly-excludable category with known debit **and** credit amounts,
   e.g. "Mortgage"), `tests/smoke.spec.js` — the assertions above **plus the edge:
   a day whose ONLY activity is an excluded category renders "No spend ●"**, not
   blank/error. Outcome: regression-guarded.

## Test Strategy

- **Unit (in-page logic via E2E harness):** `viewDay` total/received/net with an
  excluded category present; `net` unchanged when excluding a category that has both
  a debit and a credit of equal size.
- **Integration:** n/a (no server).
- **E2E (Playwright, fixture-routed):** (a) baseline total; (b) hide Mortgage in
  Settings → Month/Year/Today totals each drop by the known amount; (c) day detail
  shows the muted "Not applicable" row and the subtotal still excludes it; (d)
  HiddenNote shows the right count and opens Settings; (e) Mortgage chip absent from
  FilterBar; (f) reload → still hidden; (g) un-hide → everything restored & note gone;
  (h) **edge: a day whose only activity is Mortgage reads "No spend ●".**
  Keep zero-console-errors + 4 views × 2 editions green.
  **Harness mechanics:** drive the toggle through the UI (open gear → click the
  category row) — the real user path, exercises wiring at once. Use
  `page.addInitScript` to seed `scExcludedCats` ONLY for the "persists across reload"
  check (the app reads localStorage at `useState` init, so a post-load `evaluate`
  won't take without a reload).

## Gotchas to honor during Work
- Don't drop excluded txns from `viewDay().transactions` — the Receipt needs them.
- Handle the `dd.received === 0` flat-list early-return in Receipt (easy to miss) —
  this is the single highest-risk spot in the whole feature.
- `allCategories` must include credit-only categories too, or you can't un-hide an
  income category.
- The muted "Not applicable" section only ever appears in UNFILTERED view (excluded
  categories can't be focused, so focus mode never carries them). This is CORRECT —
  document it so it isn't later "fixed" as a phantom bug.
- Year/Month rollups route through `viewDay`/`basisAmount` (verified above) so they
  inherit exclusion automatically — the test asserts it rather than trusting it.
- Hiding ALL categories zeroes every total (every day "No spend ●") — harmless, no
  guard needed, but don't be surprised by it in manual testing.

### Ready for: Work Phase
→ `/campco-product:workflow-work` — TDD from Task 1. Reference this file:
`docs/plans/2026-06-05-not-applicable-categories.md`
