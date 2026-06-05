# Plan: Year-to-date data window (January → today)

> Date: 2026-06-05 · Feature slug: year-to-date-window
> Decision: the refresh pulls **year-to-date** (Jan 1 of the current year → today),
> replacing the trailing 90-day window. Resets each Jan 1 (accepted).

## Problem

`data/spending.json` only covers the last ~90 days (≈ March → today) because
`fetch_monarch.py` uses `LOOKBACK_DAYS=90`. Anna wants every month from January to
today populated with her real Monarch transactions.

**Critical:** this is NOT a one-time backfill. The launchd job runs `fetch_monarch.py`
and **overwrites** `spending.json` on every run, so if we only backfill now, the next
9am/4pm refresh truncates Jan–Feb right back off. The fetch *window* must change so
every refresh includes Jan→today.

## Architecture

- **No UI change.** The calendar already renders all 12 months (Year view) and
  `MIN_DATE` auto-follows `RAW_DATA[0].date`, so extending the data backfills the
  earlier months for free. We surface real data — months with no real transactions
  stay empty (we don't fabricate).
- **One knob, in the fetch window.** Change `fetch_monarch.py`'s start boundary from
  "today − 90 days" to **Jan 1 of the current year**, with an env override for
  flexibility. `build_from_mcp.py` has no window (it transforms whatever dump the
  Claude-session operator pulled) — so the only code change is in `fetch_monarch.py`.
- **Backfill = re-run the refresh.** Once the window is YTD, running
  `refresh_local.sh` (token auth, the daily path) pulls Jan→today and commits — that
  both backfills now and proves the new window works.

## Key design points

1. **Pure window helper in `aggregate.py` (NOT a new file — senior-review change).**
   `aggregate.py` is already the shared pure-logic module both scripts import, already
   has a `_selftest()` run via `python scripts/aggregate.py`, and has zero heavy deps —
   so the helper is testable without the `monarchmoney` import and needs no new test
   runner. (A new `window.py` was rejected as over-engineering for a 3-line function.)
   ```python
   from datetime import date
   def compute_window(today, start_override=None):
       """Return (start_date, end_date). Default start = Jan 1 of today's year (YTD).
       start_override (YYYY-MM-DD) wins when provided; a bad value raises ValueError
       (fail loud — it's an operator override, never silently fall back)."""
       start = date.fromisoformat(start_override) if start_override else date(today.year, 1, 1)
       return start, today
   ```
   `fetch_monarch.py` adds `compute_window` to its existing `from aggregate import …`
   and passes `MONARCH_START_DATE` (env) as the override.

2. **Replace `LOOKBACK_DAYS` with YTD + override.** `MONARCH_START_DATE` (YYYY-MM-DD)
   is the explicit escape hatch (e.g. to pull a prior year or all history); absent it,
   default is YTD. `LOOKBACK_DAYS` is retired (documented in the docstring).

3. **Paging already handles the bigger window.** `fetch_monarch.py` pages at 500/req
   until `totalCount`; ~156 YTD days is well within that. No perf concern.

## Tasks (in order) — revised per senior review

1. **Pure window helper + test (RED→GREEN)** — add `compute_window` to
   **`scripts/aggregate.py`** and extend its `_selftest()`. *Test: default →
   (Jan 1 of today's year, today); explicit override → respects MONARCH_START_DATE;
   None override → default.* Run: `python scripts/aggregate.py`. Outcome: YTD window
   logic verified in isolation, no network/heavy deps. (Manual selftest per repo
   convention — NOT gated by `npm test`; that's accepted, not "CI-covered".)

2. **Wire it into fetch_monarch.py** — add `compute_window` to the existing
   `from aggregate import …`; replace the `LOOKBACK_DAYS` start computation with
   `start, _ = compute_window(end, os.environ.get("MONARCH_START_DATE"))`; retire
   `LOOKBACK_DAYS`. Update the docstring: window semantics + a note that the **manual
   MCP path (`build_from_mcp.py`) has no window**, so a manual refresh pulls whatever
   the operator queried (don't accidentally shrink the file). A bad `MONARCH_START_DATE`
   raises `ValueError` → `main()` prints "Fetch failed" + exits 1 (loud, no
   false `auth_failed`); don't wrap it. *Verify: `python scripts/aggregate.py` passes;
   `python -c "import ast; ast.parse(open('scripts/fetch_monarch.py').read())"` compiles.*

3. **Backfill now + verify range** — run `bash scripts/refresh_local.sh`; confirm the
   committed `data/spending.json` range starts in **January 2026** and the push
   redeploys. *Verify: script prints `date range: 2026-01-xx → 2026-06-05`; capture a
   Year-view screenshot showing Jan–Jun populated as the artifact.* **Token-expired
   contingency:** if the fetch 401s, fall back to the MCP path (Monarch MCP
   `get_transactions` from Jan 1 → `build_from_mcp.py`). Outcome: the user-visible goal.

4. **Docs** — window note in `docs/HANDOFF.md` / `README.md` (data is YTD, resets Jan 1;
   `MONARCH_START_DATE` is the override escape hatch).

## Test Strategy

- **Unit (python, no network):** `scripts/window.py` `_selftest()` — default YTD,
  explicit override, None-override. This is the load-bearing logic and the only part
  testable without the live API.
- **Integration:** the live Monarch fetch can't be unit-tested (no API mock); Task 3's
  real run + printed date range is the integration check.
- **E2E:** none added — a Playwright test against the live rolling data would be flaky
  (the data changes daily). Manual Year-view confirmation in Task 3 covers it.
- Existing `npm test` (11 Playwright + `aggregate.py` selftest) must stay green — this
  change doesn't touch the data *shape*, only its date range.

## Gotchas to honor during Work
- The window change is what makes the backfill durable — without it the next refresh
  re-truncates. Land Task 2 before Task 3.
- Put `compute_window` in `aggregate.py` (no heavy deps) so its selftest runs anywhere;
  do NOT create a new module.
- Don't fabricate months — empty real months stay empty; that's expected, not a bug.
- `MONARCH_START_DATE` must parse as `YYYY-MM-DD`; a bad value fails loudly (ValueError
  → exit 1), never silently falls back.
- The window test is manual (`python scripts/aggregate.py`), not gated by `npm test` —
  accepted, matches repo convention.

### Ready for: Work Phase
→ `/campco-product:workflow-work` from Task 1. Reference:
`docs/plans/2026-06-05-year-to-date-window.md`
