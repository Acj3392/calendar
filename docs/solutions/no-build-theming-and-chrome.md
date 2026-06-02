---
title: "Light/dark theming + chrome patterns for no-build single-file React apps"
date: 2026-06-01
tags: [ui, theming, icons, prototype]
category: pattern
module: ui
symptoms: ["two line icons look identical at small size", "want dark mode without a build step", "settings panel pushes content down / jumps"]
---

# Light/dark theming + chrome patterns for no-build single-file React apps

Context: `index.html` is React-via-CDN + in-browser Babel, no build step, no
component library. These are the reusable patterns from retrofitting a polished,
Monarch-style UI (light/dark, settings popover) onto it.

## Problem

1. **Theming with no build step / no CSS framework.** Every color was an inline
   hardcoded hex, so there was no way to flip light/dark.
2. **A "gear" icon that rendered as a sun.** The first settings icon was a small
   `<circle r=3>` + eight short radial lines — geometrically that *is* a sun, and
   it sat right next to the actual sun/moon theme toggle. Two thin-stroke line
   icons of similar geometry at ~18px are indistinguishable.
3. **Settings panel shoved the page down** when it opened (content jump).

## Solution

### Theme token object + mode state (no CSS vars needed)

```js
const THEMES = {
  light: { canvas:"#f7f7f5", card:"#fff", cardBorder:"#ebebeb", text:"#1a1a1f",
           navActive:"#F4623A", tiers:{ /* per-level bg/text/accent/badge */ } },
  dark:  { canvas:"#0f1115", card:"#1c1f26", cardBorder:"#2a2e37", text:"#e8e8ec",
           navActive:"#F4623A", tiers:{ /* dark variants */ } },
};

const [mode, setMode] = useState(() => {
  try { const s = localStorage.getItem("scTheme"); if (s) return s; } catch {}
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
});
const t = THEMES[mode];                       // pass `t` through every style
useEffect(() => { document.body.style.background = t.canvas; }, [mode]); // sync overscroll
const setThemeMode = (next) => { setMode(next); try { localStorage.setItem("scTheme", next); } catch {} };
```

- Default to `prefers-color-scheme`, override with persisted `localStorage`.
- Wrap `localStorage` in try/catch (private mode / blocked storage).
- Sync `document.body.style.background` so the area outside the app container
  (overscroll / mobile rubber-band) matches the theme.

### Use a real cog path for "settings" — not circle+rays

Use the Lucide `Settings` path (toothed outer edge + center hole). A cog needs
the sinuous outer teeth; if you reduce it to a center circle with radial ticks,
you've drawn a sun. Rule of thumb: **two line icons in the same cluster must
differ in silhouette, not just interior detail, at the size they're rendered.**
The fix here also let us drop to a single header button (see below).

### Anchored popover + click-outside, no UI library

```jsx
<div style={{position:"relative"}}>
  <button onClick={()=>setOpen(o=>!o)}>…gear…</button>
  {open && (
    <React.Fragment>
      <div onClick={()=>setOpen(false)} style={{position:"fixed",inset:0,zIndex:40}}/>
      <div style={{position:"absolute",top:46,right:0,zIndex:50, /* card styles */}}>…</div>
    </React.Fragment>
  )}
</div>
```

- A `position:fixed; inset:0` transparent backdrop is the cheapest robust
  click-outside-to-close. The popover floats above content (no layout jump).
- Folding the theme toggle *into* this popover (as an "Appearance" segmented
  control) removed the twin-icon ambiguity at the source — one header button.

## Why It Works

- `const t = THEMES[mode]` makes the whole tree re-render with the new palette on
  a single state change; no CSS-variable plumbing or class toggling required.
- Stacking-context note: `position:relative` **without** a z-index does not create
  a stacking context, so the `zIndex:40` backdrop sits above the (auto-z) gear
  button. Clicking the open gear therefore closes via the backdrop — which is the
  behavior we want anyway, so no extra handling needed.

## Gotchas / known limits (not fixed here)

- Threshold sliders allow `low > high`; the `≤low` check wins, so an inverted
  config mis-classifies. One-line clamp (`high = Math.max(high, low)`) if it matters.
- Day cells are `<div onClick>` (no keyboard focus/Enter); popover has no
  Esc-to-close or focus trap. Acceptable for a personal gated prototype.

## Related

- `index.html` — `THEMES`, `GearIcon`, the settings popover, `t.tiers`
- `docs/SESSION-HANDOFF.md` — overall project state (data pipeline, deploy)
