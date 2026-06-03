---
title: "Semantic design-token + verdict-encoding pattern for the no-build app"
date: 2026-06-03
tags: [ui, design, theming, tokens]
category: pattern
module: ui
symptoms: ["want a redesign to be fast to iterate", "spend status is hard to read at a glance", "two accents but unclear when to use which", "acid-lime text is illegible on cream"]
---

# Semantic design-token + verdict-encoding pattern

Context: `index.html` is the whole app (React via CDN + in-browser Babel, no
build). The "The Daily Spend" redesign (Broadsheet × Specimen) layered a real
design system on top of the existing `THEMES[mode]` pattern from
[[no-build-theming-and-chrome]].

## Problem

1. The original styles hardcoded radius/shadow/spacing/type as magic numbers
   across ~600 lines, so changing the *look* meant a file-wide hunt.
2. Spend status (low/medium/high tiers) was encoded only as slightly different
   **text color** — too subtle to read at a glance ("did I overspend?").
3. Two accents (periwinkle + acid-lime) with no rule for which means what.

## Solution

### Typography tokens, one job each
Added a `TOKENS.type` layer alongside the per-mode color `THEMES`:
```js
const TOKENS = { type: {
  display: "'Anton', sans-serif",   // masthead nameplate ONLY
  serif:   "'Fraunces', serif",     // ALL numerals (italic when large)
  chic:    "'Syne', sans-serif",    // labels, kickers, section heads
  ui:      "'Inter', system-ui, sans-serif",
}};
```
Rule that made a bulk migration safe (a line-scoped script, not replace-all):
a style line with `...numeral` → `serif`; otherwise (a label) → `chic`; the one
nameplate line (matched by its literal text) stays `display`.

### Semantic verdict, derived once, consumed everywhere
The key move for "make overspending obvious": map the spend tier to a **verdict**
and a **cell fill**, computed in one place, and have every view read it.
```js
const verdictOf = (lvl) =>
  lvl==="high"   ? {tone:"over",    label:"Overspent"}  :
  lvl==="zero"   ? {tone:"good",    label:"No spend ●"} :
  lvl==="low"    ? {tone:"good",    label:"Met goal ✓"} :
  lvl==="medium" ? {tone:"neutral", label:"On pace"}    : null;

const cellTone = (lvl) =>
  lvl==="high"                  ? {bg:t.over,     num:"#fff",     amt:"#fff"} :
  (lvl==="low"||lvl==="zero")   ? {bg:t.goodTint, num:t.inkMuted, amt:t.ink } :
                                  {bg:"transparent", num:t.inkMuted, amt:t.ink};
```
Heatmap cells **fill** by verdict (over = solid red block, good = lime wash), so
the calendar reads good→bad instantly. `today` keeps its identity as a periwinkle
**ring** (`inset box-shadow`) layered *over* the verdict fill, so "today" and
"overspent" can both be true.

### The two-accent (now three) color rule
- **periwinkle** = structure / today / links (the neutral brand accent)
- **acid-lime** = "good / met goal / active filter" — **only ever as a fill with
  dark ink** (`accent2` + `accent2Ink`). Lime as text/outline on cream FAILS
  contrast; this rule is non-negotiable.
- **rust-red** (`over`) = overspent. Works as fill (white text) AND as
  outline/text (enough contrast on cream and charcoal).

## Why It Works

`const t = THEMES[mode]` already re-renders the whole tree on one state change.
Pushing *semantics* (verdict/tone) into the same single-source helpers means a
view never decides "what does high mean" — it just asks `cellTone(lvl)`. Changing
the whole spend-status language is a 2-helper edit, not a per-view sweep.

## Related
- [[no-build-theming-and-chrome]] — the underlying `THEMES[mode]` pattern
- `index.html` — `TOKENS`, `verdictOf`, `cellTone`, `Stamp({tone})`, `FilterBar`
- `docs/design/aspirational-direction.md` — the direction this implements
