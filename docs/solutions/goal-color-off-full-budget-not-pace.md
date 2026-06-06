---
title: "Drive a goal's alarm color off the full budget, not a linear pace line"
date: 2026-06-06
tags: [ui, ux, verdict, budgets]
category: pattern
module: ui
symptoms: ["budget/goal indicator flashes red early in the month", "every normal spend day looks over-budget", "pace line cries wolf on bursty categories"]
---

# Drive a goal's alarm color off the full budget, not a linear pace line

## Problem

Showing "did I stay under my monthly goal?" for a category (e.g. Restaurants $300/mo)
in Focus mode. The obvious implementation compares spend to a **linear pace line** —
`target = budget × elapsed/daysInMonth` — and colors red when `spent > target`. But
real spending is **bursty** (one $70 dinner on day 3), and a linear ramp gives a tiny
early-month target ($300 × 3/30 = $30), so a single normal purchase trips **red** even
though you're $230 under your actual budget. The pace line cries wolf for the first
half of every month.

## Solution

Separate the **color** (must be unambiguous) from the **pace hint** (informational):

```js
return {
  budget, spent, future, isCur,
  overBudget:  spent > budget,    // COLOR is driven by this — rust only here
  aheadOfPace: spent > target,    // TEXT hint only ("ahead of pace"), never the color
};
```

- **Rust** only when `overBudget` (you have actually exceeded the monthly budget — a
  fact that can't be wrong).
- **Calm color** (periwinkle) for every under-budget state; the words distinguish
  "on track" from "ahead of pace." Same color, different text — so being ahead of a
  linear pace never *looks* like failure.

Two more rules that fell out of the same feature:
- **Numerator and denominator must cover the same set.** When a goal sums multiple
  things (multi-category focus), sum *spend* and *budget* over the **same** subset
  (only categories that have a budget). Summing all focused categories' spend against
  a subset's budget reads falsely "over."
- **Replace, don't stack, competing yardsticks.** When the budget basis is showing,
  suppress the older relative "vs your average" text — two judgment scales on screen
  at once is confusing.

## Why It Works

A goal indicator's job is trust. Color is the loudest signal, so it must map to the
one thing that is unambiguously true (over/under the real budget). Pace/projection is
inherently noisy on lumpy data early in a period, so it belongs in text where the user
reads it as context, not alarm. The general rule: **let the loud channel carry only
the fact; let the quiet channel carry the estimate.**

## Related
- `docs/solutions/filtered-verdict-needs-own-basis.md` — Focus mode this builds on
- `docs/solutions/backfill-vs-window-on-overwriting-jobs.md` — how the budgets data lands
- Plan: `docs/plans/2026-06-06-category-budget-goal.md`
- `index.html`: `budgetStatus`, `BudgetLine`
