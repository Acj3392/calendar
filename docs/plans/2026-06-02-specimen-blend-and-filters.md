# Implementation Plan — Specimen Blend + Category Filters

> Iteration on "The Daily Spend": remove the masthead kicker, blend **The
> Broadsheet** (kept: ruled-ledger bones, newspaper nameplate, periwinkle) with
> **The Specimen** (typography + filter chips), and add **functional category
> filtering**. Built to the impeccable quality bar.
>
> Reference mockup: `docs/design/mockups.html` (Specimen + Broadsheet tabs).
> Date: 2026-06-02 · Phase: Plan / impeccable shape → **awaiting confirmation**

---

## Context

Single static `index.html` (React via CDN + Babel, no build). Builds on the
shipped Broadsheet redesign (`docs/plans/2026-06-02-the-daily-spend-redesign.md`)
and its token system (`THEMES[mode]` + `TOKENS`). This is a **visual re-skin +
one real feature (filtering)**. No DB/API/auth.

### Confirmed decisions (this session)
- **Filters = filter everything.** Selecting categories recomputes day totals,
  the heatmap tiers, ledgers, and all summary figures to the chosen categories.
- **Typography = full Specimen.** Big numbers → **italic Fraunces**; labels /
  kickers / section heads / day-of-week → **Syne**. *Decision I'm making:* keep
  **Anton for the masthead nameplate only** — it's the one Broadsheet signature
  that makes the "newspaper × type-foundry" blend read as a blend, not a
  replacement. (Flag if you'd rather the nameplate also go Syne/Fraunces.)
- **Accent = periwinkle + acid-lime**, with **semantic roles** (not decoration):
  - **Periwinkle** `#6c5cf6` = primary/structure: today, high spend, links, nameplate accents.
  - **Acid-lime** = "good / active": low-spend ✓, $0 days, and **active filter chips**.
    Used as a *fill with dark ink* (never lime text on cream; fails contrast).

### Impeccable notes folded in
- **Remove the em dash** in the masthead dateline (banned). Use a middot.
- Keep the existing **hex token system** rather than converting to OKLCH —
  deliberate, for consistency with the no-build codebase. Neutrals already warm-tinted.
- **No side-stripe borders, no gradient text, no glass, no modals** (DayDetail
  stays inline). Today view avoids the hero-metric cliché via editorial type + stamp.
- Filter chips are real `<button>`s with `aria-pressed`; scrollable, keyboard-reachable.

### The 42-category constraint
The data has **42 categories** (Mortgage $14.7k, Restaurants $2.1k, Groceries
$1.8k, Pets, Home Improvement, Fitness… long tail). A flat chip row won't fit.
**Approach:** a single horizontally-scrollable filter bar, chips ordered by total
spend (biggest first), with an "All" reset pinned at the start. The long tail is
reachable by scroll. (No dropdown, no modal.) `log`-style note: nothing is hidden,
just ordered.

---

## Architecture

- **Fonts (`<head>`):** add **Syne** (600/700/800) to the existing Anton +
  Fraunces + Inter link.
- **Tokens:**
  - `TOKENS.type.chic = "'Syne', sans-serif"` (labels). `serif` (Fraunces) carries
    numerals; add italic at call sites for big figures. `display` (Anton) → nameplate only.
  - `THEMES.light/dark`: add `accent2` (acid-lime fill) + `accent2Ink` (dark ink on it).
- **Filter state (new):** `const [activeCats, setActiveCats] = useState([])` —
  empty = no filter (all). Multi-select toggle.
- **Category list (derived, memoized):** unique `tx.category` across `RAW_DATA`,
  summed and sorted by total desc.
- **Filter application (the core wiring):** a memoized helper
  `viewDay(dd) → { total, transactions }` that, when `activeCats` is non-empty,
  returns only matching transactions and their summed total; otherwise returns the
  day as-is. Every view reads `viewDay(dd)` instead of `dd.total` / `dd.transactions`.
  `getDateLevel` uses the filtered total so the heatmap re-skins live.
- **Filtered indicator:** when a filter is active, the active chips ARE the
  indicator; add a tiny "showing N categories · $X" line under the bar.

### Type/accent migration map (mechanical)
| Currently `TOKENS.type.display` (Anton) | Becomes |
|---|---|
| Masthead nameplate | **stays Anton** |
| Kickers ("SPENT TODAY"), section heads ("THE MONTH IN FULL"), day-of-week, popover labels, stamp, errata "STOP PRESS" | **Syne** (`TOKENS.type.chic`) |
| Hero total, DayDetail total, section/month/week/year totals | **Fraunces italic** |
| Grid + ledger amounts | **Fraunces** (upright) |

---

## UI/UX Delivery Plan

- **Journey:** Anna lands → reads today's lead → taps one or more category chips
  → entire calendar + figures recompute to those categories → taps "All" to clear.
- **Wiring matrix:** chip tap → `setActiveCats` toggle → `viewDay`/`getDateLevel`
  recompute → every view + summary figure re-renders → active chips + "showing N"
  reflect state. "All" → clears.
- **State matrix:** no filter (all) · 1+ active · **filter yields nothing** for a
  day (→ that day reads as $0/none) · **filter yields nothing all-month** (→ an
  editorial empty line: "No <category> spending this month.") · loading/error
  (unchanged).
- **UX constraints:** chip bar scrolls horizontally on mobile without clipping;
  active state legible in both editions; tap targets ≥32px; chips keyboard- and
  screen-reader-operable (`aria-pressed`).

---

## Tasks (in order)

**Task 1 — Foundation: Syne, tokens, masthead cleanup**
- Files: `index.html` (`<head>`, `TOKENS`, `THEMES`, masthead)
- Do: load Syne; add `type.chic` + `accent2`/`accent2Ink` (light + dark);
  **remove the kicker row** (No. / Personal Edition); rebuild dateline in Syne,
  **no em dash**; do the Anton→Syne (labels) / Anton→Fraunces (numerals) migration
  across all views.
- Verify: all 4 views, both editions, render; nameplate still Anton; 0 console errors.

**Task 2 — Today view, Specimen treatment**
- Files: `index.html` (`TodayView`, `Stamp`)
- Do: hero total in **giant italic Fraunces**; Syne kickers; keep stamp; tune air.
- Verify: data / zero / no-data states; legible both editions.

**Task 3 — Filter bar (UI + state + derivation)**
- Files: `index.html` (new category derivation, `activeCats` state, `FilterBar`)
- Do: derive sorted categories; scrollable chip bar with "All" reset; active =
  acid-lime fill + ink; `aria-pressed`; "showing N · $X" line.
- Verify: chips render, toggle visibly, scroll on overflow, "All" clears.

**Task 4 — Wire filter through every view**
- Files: `index.html` (`viewDay` helper; Today/Week/Month/Year/DayDetail; getDateLevel)
- Do: route all totals/transactions/tiers through `viewDay`; month/week/year
  summary totals reflect filter; empty-filter editorial lines.
- Verify: pick "Restaurants" → calendar + figures recompute everywhere; pick a
  second category → adds; "All" → restores; pick a category with no data in view → graceful.

**Task 5 — Impeccable polish pass**
- Files: `index.html`
- Do: spacing rhythm (vary, not uniform); contrast-check acid-lime + periwinkle on
  cream and charcoal; chip toggle micro-motion (ease-out, no layout animation);
  reduced-motion respected; final em-dash / copy sweep; a11y check.
- Verify: critique against impeccable shared laws + bans; both editions × 4 views.

**Task 6 — Update smoke test + re-verify**
- Files: `tests/smoke.spec.js`
- Do: extend smoke to toggle a filter chip and assert zero console errors;
  screenshot filtered state.
- Verify: `npm test` green; screenshots for all views × editions × filtered.

---

## Test Strategy
- **Automated:** extend the Playwright smoke (zero console errors; toggle a filter;
  screenshot all views × both editions × a filtered state). Runs in CI.
- **Manual checklist:** per-task Verify lines, against real `data/spending.json`.
- **Filter correctness:** selecting "Groceries" makes month total ≈ $1,835; "All"
  restores full totals; multi-select sums; empty result reads gracefully.
- **Regression:** view tabs, nav, day select, thresholds, theme persistence, errata strip.

## Out of scope
- Persisting filter selection across reloads (could add to localStorage later).
- The Landscape waveform / motion budget (still deferred).
- OKLCH migration (keeping hex token system).

## Ready for: Work Phase — **pending your shape confirmation**
This doubles as the impeccable shape brief. Confirm (or adjust the nameplate-font
flag) and I'll start at Task 1.
