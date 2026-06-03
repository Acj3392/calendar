# Implementation Plan — "The Daily Spend" Redesign + Robustness

> Redesign the spending calendar (`index.html`) to the **Broadsheet /
> "The Daily Spend"** direction — *and* harden the product so it can't silently
> break.
> Reference mockup: `docs/design/mockups.html` (Broadsheet tab).
> Direction doc: `docs/design/aspirational-direction.md`.
>
> Date: 2026-06-02 · Phase: Brainstorm + Plan → ready for Work

---

## Context & constraints (this is NOT the starter-kit stack)

Single static `index.html` — React via CDN + in-browser Babel, **no build step,
no backend, no database, no auth, no test runner.** Data is a committed JSON file
(`data/spending.json`), refreshed daily by a launchd job (see
`docs/solutions/monarch-auth-and-refresh.md`). Standard Plan layers
(DB / API / auth) are **N/A**. Reuse the established `THEMES[mode]` token pattern
(`docs/solutions/no-build-theming-and-chrome.md`); extend, don't replace.

---

## Brainstorm summary — robustness

### Why (the fragilities we're fixing)
1. **CDN runtime = single point of failure.** App loads React **development**
   builds + Babel-standalone from unpkg at runtime; an unpkg blip = white screen,
   and we ship the slow dev build.
2. **No safety net.** A bad JSX expression blanks the page silently — no error
   boundary, no test/CI guard.
3. **Data layer trusts input.** `spending.json` parsed without shape validation
   (malformed → crash); fetch failure has no retry; `low > high` threshold
   inversion bug.
4. **Refresh failure is a blunt signal.** The >26h stale banner can't distinguish
   "missed run" from "token expired" — the case that needs Anna's intervention.

### Decisions (confirmed with Anna)
**Redesign**
- **Accent:** periwinkle `#6c5cf6` **replaces coral everywhere**.
- **Themes:** keep **both** — light "Day Edition" + dark **"Night Edition"**.
- **Markers:** **replace emoji** (🏆/💚) with print-native marks (✓, ●, rules) +
  rotated overprint stamp.

**Robustness** (scope = *Resilience essentials + tests*)
- **Runtime:** pin exact versions, switch to **production** React builds, add
  **SRI + `crossorigin`**. Stays no-build; kills white-screen-from-CDN; faster.
- **Error boundary:** graceful "couldn't render" card instead of a blank page.
- **Data layer:** validate `spending.json` shape on load; retry fetch (2× w/
  backoff); **clamp `high = max(high, low)`**.
- **Tests:** one **Playwright smoke** (loads app, asserts zero console errors,
  screenshots 4 views × 2 themes) + a **GitHub Action** running it. Node deps are
  dev/CI-only — the app itself stays no-build.
- **Refresh signaling:** `fetch_monarch.py` / `build_from_mcp.py` stamp a
  `refreshStatus` (`ok` / `auth_failed`) into the JSON; the banner reads it to say
  *"token expired — re-auth"* vs *"refresh missed."*

### Assumptions (low-impact, not asked)
- Full a11y pass (keyboard nav, focus trap) stays **deferred** (not in
  essentials+tests scope) — but trivial wins (Esc-to-close popover, threshold
  clamp) are folded in.
- Vendoring libs locally was offered but **not** chosen; pinning + SRI is enough.
- Playwright serves the app via `python -m http.server` in CI (no app build).

---

## Architecture

- **Database / API / AI:** N/A (static site).
- **State:** unchanged `SpendingCalendar` state. Add a top-level **ErrorBoundary**
  class wrapper and harden the **bootstrap** fetch (validation + retry).
- **Design-token layer (core change):** extend `THEMES` + add shared `TOKENS`:
  - `type`: `{ display:"'Anton',sans-serif", serif:"'Fraunces',serif", ui:"'Inter',sans-serif" }`
  - `rule`: hairline/heavy/double rule colors + newsprint **grain** value
  - `accent`: periwinkle (+ muted tint)
  - per-theme `paper`, `ink`, `inkMuted`, `ruleHair`, `ruleBold`
  - keep 5-tier spend scale, re-tuned to a warm print ramp; route high+today
    through periwinkle.
- **Fonts (`<head>`):** add **Anton** (display numerals), **Fraunces** (ital +
  roman), keep **Inter**. Pin font CSS too.
- **Runtime (`<head>`):** pinned `react@18.x` + `react-dom@18.x` **production.min**
  + pinned `@babel/standalone`, each with `integrity` + `crossorigin`.
- **Data contract addition:** `spending.json` gains `refreshStatus` + keeps
  `generatedAt`. Validator tolerates its absence (back-compat).

### Design system — "The Daily Spend"
| Element | Treatment |
|---|---|
| Masthead | "THE DAILY SPEND" in Anton, edition kicker, Fraunces-italic dateline, `3px double` rule |
| Big numerals | Anton condensed; periwinkle for emphasis |
| Editorial voice | Fraunces italic (summaries, empty/error states, captions) |
| Grid | hairline-ruled ledger table (`border-right`/`border-bottom`) |
| Today / high spend | periwinkle fill or ink |
| Status | rotated overprint stamp + ✓/● marks |
| Ground | warm newsprint + faint dot-grain |
| Labels | tiny, wide-tracked, uppercase |

---

## UI/UX Delivery Plan

- **User journey:** Anna opens the gated app → today's spend as the "lead story"
  → scans the month ledger → drills into a day → switches views/themes/thresholds.
  If a refresh failed, the errata strip tells her *exactly* what to do.
- **Wiring matrix** (UI action → state → result): view tabs → `setView`; day tap
  → `toggleDay` → ledger DayDetail; month/week nav → grid re-render; year card →
  month view; gear → `THEMES[mode]`/thresholds re-skin; `refreshStatus`/age →
  errata strip; fetch fail → retry then error card.
- **State matrix (per view):** data · zero-spend · no-data (`—`) · today ·
  loading (masthead skeleton) · fetch-error (Fraunces error card) · stale/auth.
- **UX constraints:** mobile-first (≤520px container); verify Anton legibility at
  small sizes; periwinkle-on-paper text contrast; tap targets ≥38px.

---

## Tasks (in order)

Each task is independently browser-verifiable (`open index.html`). Verify the
checklist before moving on.

**Task 1 — Runtime & data hardening** *(robustness foundation)*
- Files: `index.html` (`<head>`, bootstrap, top-level wrapper)
- Do: pin React/ReactDOM **production.min** + Babel standalone with SRI +
  `crossorigin`; add an **ErrorBoundary** class around `SpendingCalendar`;
  validate `spending.json` shape on load (array of `{date,total,transactions}`),
  fall back to the error card on bad data; **retry fetch 2× w/ backoff**; clamp
  `high = Math.max(high, low)`.
- Verify: app loads (prod builds, no console errors); kill network → retry then
  graceful error card; feed malformed JSON locally → error card, not blank; set
  low>high in settings → classification stays sane.

**Task 2 — Design foundations: fonts, tokens, masthead, grain**
- Files: `index.html` (`<head>` fonts; `THEMES` + `TOKENS`; shell/header)
- Do: add Anton/Fraunces; build token layer (type/rule/accent/paper/ink/grain);
  newsprint dot-grain ground; replace header with masthead (title + edition
  kicker + dateline + double rule); coexist nav tabs + gear; swap accent
  coral→periwinkle in shared button styles.
- Verify: fonts render, grain visible, masthead correct, nav+gear work, no errors.

**Task 3 — Today view = the "lead story"**
- Files: `index.html` (`TodayView`)
- Do: Anton lead number; Fraunces-italic summary column; periwinkle; overprint
  status stamp; transactions as ruled ledger rows; data/zero/no-data states.
- Verify: all three states; stamp + marks; tabular numerals.

**Task 4 — Month view = ledger table + DayDetail**
- Files: `index.html` (`MonthView`, `DayDetail`)
- Do: hairline-ruled table grid; Fraunces day numbers + Anton amounts; periwinkle
  for today/high; "The Month in Full" head; restyle `DayDetail` as ruled ledger
  panel; typographic marks replace emoji.
- Verify: reads as a ledger; today highlighted; DayDetail ruled rows; marks right.

**Task 5 — Week view**
- Files: `index.html` (`WeekView`)
- Do: 7-column ruled strip consistent with month; preserve auto-select-today;
  editorial week-nav label; shared DayDetail.
- Verify: renders, today auto-selected, nav works, consistent.

**Task 6 — Year view = the "annual report"**
- Files: `index.html` (`YearView`)
- Do: 12 month sections as newspaper columns; mini ruled grids / dot rows in the
  periwinkle ramp; Anton month totals; click → month view preserved.
- Verify: 12 months, ramp reads, click-through works.

**Task 7 — refreshStatus pipeline** *(robustness — Python)*
- Files: `scripts/fetch_monarch.py`, `scripts/build_from_mcp.py`
- Do: write `refreshStatus` (`ok` on success; `auth_failed` on token/auth error)
  alongside `generatedAt` into `spending.json`; keep output back-compatible.
- Verify: run each script; inspect JSON has `refreshStatus`; simulate auth failure
  path sets `auth_failed`.

**Task 8 — Chrome: popover, month switcher, errata strip**
- Files: `index.html` (settings popover, month switcher, stale banner)
- Do: restyle popover (Appearance control, sliders w/ periwinkle `accentColor`,
  re-tuned tier legend) in Broadsheet language; month switcher as dateline nav;
  rebuild the banner as a **refreshStatus-aware errata strip** —
  `auth_failed` → "Token expired — re-auth (see handoff)"; else >26h → "Refresh
  missed"; add Esc-to-close on popover (trivial a11y win).
- Verify: popover opens/closes (backdrop + Esc); sliders re-skin live; legend
  matches ramp; force `auth_failed` and stale → correct distinct messages.

**Task 9 — Night Edition (dark) + consistency/polish**
- Files: `index.html` (`THEMES.dark`, cross-view cleanup)
- Do: tune dark to charcoal-newsprint "Night Edition" (periwinkle holds, grain
  adapts); remove every leftover coral + emoji; `tabular-nums` everywhere;
  Anton min-size legibility check; consistency sweep both themes × 4 views.
- Verify: toggle light/dark across all views — cohesive, no coral, no emoji,
  legible, no console errors.

**Task 10 — Playwright smoke + GitHub Action** *(robustness — tests)*
- Files: `tests/smoke.spec.js` (or `e2e/`), `package.json` (dev deps + script),
  `.github/workflows/smoke.yml`, `.gitignore` (node_modules)
- Do: Playwright test that serves the app (`python -m http.server`), loads it,
  asserts **zero console errors**, visits all 4 views × 2 themes and screenshots
  each; GH Action installs Playwright + runs it on push/PR.
- Verify: `npx playwright test` green locally; Action green on a test push;
  screenshots produced.

**Task 11 (optional / deferred) — Motion budget**
- Files: `index.html`
- Do: count-up digits on the hero number + a shared-element-ish day-open reveal;
  respect `prefers-reduced-motion`.
- Verify: subtle, non-janky. Ship 1–10 first.

---

## Test Strategy

- **Automated smoke (new — Task 10):** Playwright loads the app, asserts **zero
  console errors**, screenshots 4 views × 2 themes; runs in **CI** on every push.
  This is the primary regression guard given the single-file architecture.
- **Manual checklist (per task):** the Verify lines above, run against real
  `data/spending.json`.
- **Resilience checks (Task 1):** network-off → retry then error card; malformed
  JSON → error card not blank; low>high → sane classification.
- **Refresh checks (Tasks 7–8):** JSON carries `refreshStatus`; banner shows
  distinct `auth_failed` vs missed-run messages.
- **Regression:** view tabs, month/week nav, year→month drill, day select,
  thresholds, settings open/close, theme persistence across reload.

---

## Out of scope
- Data pipeline beyond `refreshStatus` (Monarch fetch logic untouched).
- The Landscape waveform "Year in Spending" (different direction; future feature).
- **Full** a11y pass (keyboard cell nav, focus trap) — deferred; only trivial
  wins (Esc-to-close, threshold clamp) included.
- Vendoring libs locally (pinning + SRI chosen instead).
- A real build step — stays no-build for the app; Node is dev/CI-only.

## Ready for: Work Phase
Start at Task 1 (runtime & data hardening — the safety net), then Task 2 onward.
Verify each checklist before proceeding.
