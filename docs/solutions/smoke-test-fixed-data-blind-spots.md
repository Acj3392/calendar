---
title: "Fixed-data smoke tests miss state-dependent render branches"
date: 2026-06-03
tags: [testing, ui]
category: gotcha
module: testing
symptoms: ["smoke test green but a code path still crashes", "ReferenceError only on certain data", "refactor removed a const but tests passed"]
---

# Fixed-data smoke tests miss state-dependent render branches

## Problem

The Playwright smoke test loads the app against the **real** `data/spending.json`
and asserts zero console errors across all views and editions. It passed — yet a
real crash shipped: `TodayView` referenced `isLow` after its `const` was removed
during a refactor. A low-spend *today* would throw a `ReferenceError`.

It slipped through because **today (June 2) happens to be a $0 day**, so the
`note` ternary short-circuited at `isZero` and never evaluated the `isLow`
branch. The smoke can only exercise whatever state the live data produces.

(The app's `ErrorBoundary` would have shown a graceful card instead of a blank
page in production, but it was still a bug a user could hit.)

## Solution

1. **After a refactor that removes a `const`, grep for the identifier** before
   trusting tests:
   ```bash
   grep -n "isLow\|amtColor\|isHigh" index.html
   ```
   In a no-build app there is no compiler/linter to flag a dangling reference;
   it only throws at render time, on the branch that uses it.
2. Prefer **inline conditions over derived booleans** in branchy render code
   (`lvl==="low"` instead of a `const isLow` defined far away) so a removed
   declaration can't leave a live reference.
3. Know the blind spot: a fixed-data smoke covers *today's current state* only.
   Branches gated on data that today doesn't hit (e.g. TodayView's non-zero
   verdict copy) are unreachable without mocking `TODAY`. Views that iterate all
   days (Month/Week/Year) DO exercise every tier, so put logic there when you can.

## Why It Works

In-browser Babel transpiles but does not do static analysis. An unused/removed
`const` is only an error when the line that reads it actually runs. Coverage is a
function of the input data, so "green smoke" means "no errors *for this data*",
not "no errors".

## Update (2026-06-03): the credits work added two more blind-spot lessons

1. **Route a committed fixture for feature assertions, not the live window.**
   Credit-rendering assertions can't depend on `data/spending.json` (a rolling
   90-day window — income/refunds may not be present). The smoke test now
   `page.route()`s `**/data/spending.json` to `tests/fixtures/spending.sample.json`,
   which guarantees a credit day, a refund-offset day, and a pure-income day. Live
   data is left untouched, so the credit tests are deterministic.

2. **A fixture must mirror real data's *messiness*, not just its happy path.**
   The credit-chip de-dup bug (a category that is both debit and credit getting a
   redundant second chip) shipped green because the fixture's credit categories
   never *overlapped* a debit category — real data has 16 such overlaps. The fix
   added an overlapping category (a Groceries return) to the fixture so the
   regression is actually exercised. When a fixture is "too clean," it tests a
   world your users don't live in.

## Related
- `tests/smoke.spec.js` — the smoke test
- `tests/fixtures/spending.sample.json` — the credit fixture (overlap included)
- `index.html` — `ErrorBoundary` (the safety net that downgrades such bugs)
- [[credits-and-net-basis]] — the feature these lessons came from
- Fixed in commit `a6c097b`
