# Plan: Category budget goal in Focus mode

> Date: 2026-06-06 · Feature slug: category-budget-goal
> Builds on the shipped data layer (`spending.json.budgets[YYYY-MM][category]`) and
> Focus mode (`docs/solutions/filtered-verdict-needs-own-basis.md`).

## Decisions (from brainstorm + clarifying answers)

- **Day cells: NO change to per-cell verdicts.** When focused, cells already show
  the filtered category's spend (Focus mode). We do not paint budget verdicts onto
  individual days. (Anna: "the day cells will only change in that the number they
  reflect will be solely the filtered list total" — that's existing behavior.)
- **Budget judged at the SUMMARY level**, not per cell: a header readout
  *"Restaurants · $180 of $300 · on track"*.
- **Monthly budget + pace.** For the current month, prorate the target by days
  elapsed. Past month = actual vs budget. Future month = budget only.
- **Multi-category focus: SUM the budgets** of focused categories that have one.
- **Gross spend vs budget.** Monarch planned amounts are spend budgets, so the
  readout always compares GROSS filtered spend to the budget, independent of the
  Spend/Net toggle (the toggle still governs the existing cell numbers/verdicts).

## Architecture

- **No backend / pipeline change** — budgets already ship in `spending.json`
  (verified: months 2026-05/06/07, all carry "Restaurants & Bars" etc.).
- **Parse:** add `let BUDGETS = {};` (near index.html:36) and `BUDGETS = j.budgets || {};`
  in the loader (index.html:1213 area, beside `RAW_DATA = j.data`).
- **Purely additive UI.** Existing `filteredThresholds` / `getLevel` / `getDateLevel`
  / cell rendering are UNTOUCHED. We only add a budget summary block in the focus
  headers.

### New pure helpers (in index.html, tested via E2E with a budget fixture)
**Critical: spend and budget must sum over the SAME category set** — only cats that
have a budget that month (`budgetedCats`). Summing all focused cats' spend against a
subset's budget would falsely read "over" (review fix #1).
```js
const budgetStatus = (monthKey, cats) => {
  const m = BUDGETS[monthKey];
  const budgetedCats = m ? cats.filter(c => typeof m[c] === "number") : [];
  if (!budgetedCats.length) return null;                 // none budgeted → relative fallback
  const budget = budgetedCats.reduce((s,c) => s + m[c], 0);
  // gross spend (debits only) for the SAME budgeted cats, in this month
  const spent = RAW_DATA.reduce((s,d) =>
    d.date.slice(0,7) !== monthKey ? s :
    s + d.transactions.reduce((t,tx) =>
      (!isCredit(tx) && budgetedCats.includes(tx.category)) ? t + tx.amount : t, 0), 0);
  const cur    = TODAY.slice(0,7);
  const future = monthKey > cur;                          // review fix #3: no status for future
  const isCur  = monthKey === cur;
  const dim    = new Date(+monthKey.slice(0,4), +monthKey.slice(5,7), 0).getDate();
  const elapsed = isCur ? Math.max(1, +TODAY.slice(8,10)) : dim;  // past → full month
  const target  = budget * (elapsed / dim);              // prorated pace line (for the hint only)
  return {
    budget, spent, future, isCur,
    overBudget:  spent > budget,        // review fix #2: COLOR is driven by this (unambiguous)
    aheadOfPace: spent > target,        // secondary text hint only, never the color
  };
};
```
**Color rule (review fix #2):** rust only when `overBudget` (you've actually exceeded
the monthly budget); lime otherwise. `aheadOfPace` is *text* ("ahead of pace" vs
"on track"), never the alarming color — a linear pace line trips constantly early in
a bursty month, so it must not drive red.

## UI/UX Delivery Plan

- **User journey:** Anna filters to Restaurants → each day card shows only restaurant
  spend (existing) → a budget line in the view header reads *"$180 of $300 · on track"*
  (lime) or *"over pace"* (rust) so she knows at a glance whether she's within her
  Monarch budget for the month.
- **Surfaces (v1):** **Month** header (primary) + **Today** header, both rendering ONE
  shared `<BudgetLine monthKey={...}/>` component (review fix #5 — no duplicated markup;
  each view passes its own month: Month → `currentMonth`, Today → `TODAY` month). Week
  and Year are out of v1 (budgets only cover 3 months) — stated, not silently dropped.
- **Replaces, not stacks (review fix #4):** when `budgetStatus` is non-null for the
  viewed month, the budget line REPLACES the existing "judged vs $X/day avg" relative
  strip text — never show both yardsticks at once. No budget → relative strip as today.
- **Copy by tense (review fix #6):** current month → "on track" / "ahead of pace" (and
  "over budget" if `overBudget`); past month → "under budget" / "over budget" (no "pace"
  wording for a finished month); future month → budget only, no status.
- **Wiring matrix:**
  | State | Header shows |
  |---|---|
  | Focused, category has a budget for the viewed month | `{cat} · ${spent} of ${budget}` + on track / over pace (prorated for current month) |
  | Focused, no budget for that month/category | existing relative-average strip (`vs $X/day avg`) — unchanged |
  | Not focused | unchanged |
- **State matrix:** under-pace (lime), over-pace (rust), past-month under/over (actual
  vs full budget), future-month (budget only, no status), no-budget (relative fallback).
- **UX constraints:** budget line uses existing tokens (lime = good, rust = over,
  `fmtAmt`); readable on both editions; the existing Focus pill stays.

## Tasks (in order) — revised per senior review

1. **Parse budgets + `budgetStatus` + `<BudgetLine>` in Month (first visible slice)** —
   `index.html`: `BUDGETS` global + loader line; `budgetStatus` (with `budgetedCats`
   alignment, full-budget color, `future` flag); a shared `<BudgetLine monthKey>`
   component; render it in MonthView, REPLACING the relative-strip text when non-null.
   *E2E (budget fixture, pinned today): focus Restaurants in Month → "$120 of $300 · on
   track" (lime).* Outcome: the core feature, visible. (Merged former 1+2 — helpers alone
   aren't user-visible.)

2. **`<BudgetLine>` in Today** — render the same component in TodayView with TODAY's
   month. *E2E: Today focused shows the month budget line.* Outcome: parity on the daily
   surface.

3. **Fixture + smoke assertions** — `tests/fixtures/budget.sample.json` with a **pinned
   `today` (day 15 of a 30-day month)** and amounts that hit all three color/text states:
   under pace ($120 → lime "on track"), over pace but under budget ($200 → lime "ahead of
   pace"), over budget ($320 → rust "over budget"); plus a no-budget category (relative
   fallback) and multi-category alignment. `tests/smoke.spec.js`.

## Edge cases to honor

- **No budget for the focused category/month** → no readout; existing relative strip
  shows (no regression). Most important fallback.
- **Multi-category focus** → sum budgets of focused cats that have one (Anna's choice);
  if none have a budget → relative fallback.
- **Partial (current) month** → prorate target by days elapsed; past month → full budget;
  future month → show budget, no over/under status.
- **Net/credits** → readout compares GROSS spend to budget regardless of Spend/Net toggle
  (budgets are spend budgets); a refund doesn't shrink the budget line. Label "spent".
- **Hidden ("not applicable") categories** → can't be focused, so never get a budget
  readout. No special handling.
- **Budget coverage = 3 months only** → viewing a month outside May–Jul → relative
  fallback. This is why Year is out of v1 (most months uncovered).
- **Budget = 0 / missing** → treated as no budget → relative fallback.

## Test Strategy

- **Unit:** the helpers are pure but live in index.html (no JS unit harness) → exercised
  via E2E against a deterministic fixture rather than mocked.
- **E2E (Playwright, `budget.sample.json`, pinned today = day 15/30):** (a) focus
  Restaurants in Month → "$120 of $300"; (b) under pace → "on track" + lime;
  (c) over pace but under budget → "ahead of pace" + lime (NOT rust — the false-alarm
  guard); (d) over budget → "over budget" + rust; (e) no-budget category → relative
  "vs avg" strip still shows, no budget line; (f) Today surface shows the month budget
  line. Keep zero-console-errors + existing 11 green.
- **No data-shape regression** — `budgets` is already in the live file; this only reads it.

### Ready for: Work Phase
→ `/campco-product:workflow-work` from Task 1. Reference:
`docs/plans/2026-06-06-category-budget-goal.md`
