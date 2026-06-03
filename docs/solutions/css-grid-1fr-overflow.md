---
title: "CSS grid repeat(N,1fr) overflows when a cell's content is wide"
date: 2026-06-03
tags: [ui, css, layout]
category: gotcha
module: ui
symptoms: ["calendar Saturday column clipped off the right edge", "grid wider than its container", "columns uneven when one cell has a long number"]
---

# repeat(N,1fr) overflows on wide content

## Problem

The month/week calendars use `gridTemplateColumns: "repeat(7,1fr)"`. In Net mode,
some cells show wide net-gain amounts like `+$3.7k`. Those cells pushed their
column wider than 1/7 of the container, so the whole row exceeded the page width
and the Saturday column was clipped off the right edge. Spend mode looked fine
only because its numbers happened to be narrower.

## Solution

```js
// before
gridTemplateColumns: "repeat(7,1fr)"
// after
gridTemplateColumns: "repeat(7,minmax(0,1fr))"
```

Applied to every 7-column grid (week strip, month weekday header, month cells,
year mini-grids) so the header and body stay aligned.

## Why It Works

`1fr` is shorthand for `minmax(auto, 1fr)`, and `auto` resolves to the track's
**min-content** width. A cell with non-wrapping text (a long `$` figure) has a
large min-content, so the column refuses to shrink below it and the sum of tracks
exceeds the container → horizontal overflow. `minmax(0, 1fr)` sets the minimum to
`0`, letting columns shrink to an equal share and keeping the grid contained
(content clips/wraps inside the cell instead of blowing out the layout).

This is the canonical fix for "my flex/grid item won't shrink" — the same reason
`min-width: 0` is needed on flex children.

## Related
- [[credits-and-net-basis.md]] — Net mode is what surfaced the wide numbers
- `index.html` — WeekView / MonthView / YearView grids
