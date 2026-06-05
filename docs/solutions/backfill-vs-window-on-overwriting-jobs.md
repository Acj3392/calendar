---
title: "A backfill won't stick if a scheduled job overwrites the output — change the window"
date: 2026-06-05
tags: [deployment, data, pipeline]
category: gotcha
module: deployment
symptoms: ["data only goes back ~90 days", "older months keep disappearing after a refresh", "I backfilled but it got truncated", "want every month from January"]
---

# A backfill won't stick if a scheduled job overwrites the output

## Problem

`data/spending.json` only covered the last ~90 days. The instinct is "backfill the
missing months." But `fetch_monarch.py` doesn't *append* — it **regenerates the whole
file** from a trailing 90-day Monarch query, and the launchd job runs it twice daily.
So any manual backfill (MCP pull, hand-edit) gets **wiped on the next scheduled run**.
The visible data is an *output* of the window, not an accumulating store.

## Solution

Change the **window**, not the data. The window lived in one place
(`LOOKBACK_DAYS=90` → `start = today − 90d`). Replaced it with a year-to-date start,
extracted as a pure, testable helper in `aggregate.py` (the shared pipeline module —
no new file, reuses the existing `_selftest()` runner):

```python
def compute_window(today, start_override=None):
    # Default = Jan 1 of today's year (YTD); MONARCH_START_DATE overrides; bad value raises.
    start = date.fromisoformat(start_override) if start_override else date(today.year, 1, 1)
    return start, today
```

Then `fetch_monarch.py` uses it, and re-running the refresh both backfills *and*
proves the change. Crucial ordering: **land the window change before backfilling**,
or the backfill is throwaway.

## Why It Works

For an **idempotent, overwriting** producer, the output is a pure function of its
inputs (here, the date window). You don't fix the output; you fix the input that
regenerates it — then every future run reproduces the desired result for free. The
trap is treating a regenerated artifact like an accumulating database: edits to the
artifact have no memory.

Decision recorded: window is **year-to-date** (resets each Jan 1), chosen over a
rolling 12-month window. `MONARCH_START_DATE=YYYY-MM-DD` is the escape hatch for a
prior year / all history.

Verification for an un-mockable live fetch: the pure window logic gets a real unit
test (`compute_window` selftest); the fetch itself is verified by an actual run that
prints its date range — and, here, by triggering the **scheduled** job (`launchctl
start`) so the real cron path is exercised, not just a manual invocation.

## Related
- `scripts/aggregate.py` — `compute_window` + selftest
- `scripts/fetch_monarch.py` — token-path window (defines the range)
- `scripts/build_from_mcp.py` — manual MCP path has NO window (operator sets it)
- `docs/solutions/monarch-auth-and-refresh.md` — the refresh pipeline + launchd job
- Plan: `docs/plans/2026-06-05-year-to-date-window.md`
