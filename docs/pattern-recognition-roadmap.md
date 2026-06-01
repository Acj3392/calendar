# Pattern Recognition — Future Roadmap

> Status: **idea / not yet built.** This documents where the calendar could go once
> the live-data pipeline is stable. Nothing here is implemented yet.

## The goal

Today the calendar *shows* spending. The next step is for it to *notice things* —
to surface relationships between categories over time that a person wouldn't spot
by scanning a grid of daily totals.

## Motivating example

The pattern I most want it to catch is **substitution between categories**:

> When **grocery** spending goes up, does **DoorDash / Restaurants** spending go down
> by roughly the same amount?

If groceries climb \$200 in a month while delivery drops \$180, that's not \$380 of
new spend — it's a behavior shift that nets close to flat. The calendar should be
able to say something like:

> "Your groceries are up \$200 this month, but DoorDash is down \$180 — looks like
> you're cooking more. Net food spend is about the same."

That reframing is the whole point: **celebrate the behavior change**, not just the
raw dollar movement. It fits the project's original spirit — celebrating the good
days rather than scolding the expensive ones.

## Patterns worth detecting (rough priority)

1. **Category substitution** — two categories that move in opposite directions
   (groceries ↔ delivery, rideshare ↔ EV charging, etc.). The headline feature.
2. **Trend / drift** — a category quietly rising or falling week over week.
3. **Recurring rhythm** — predictable cadence (mortgage on the 1st, a weekly coffee
   habit) so anomalies stand out from the normal beat.
4. **Anomaly / spike** — a day or merchant well outside the usual range.
5. **Streaks** — consecutive low-spend or \$0 days (ties directly into the green-day
   celebration already in the UI).

## How it could work (sketch, not a commitment)

- **Inputs:** the same `data/spending.json` we already produce, aggregated by
  category and by week/month rather than just by day. No new data source needed —
  the transaction-level `category` field is already there.
- **Substitution detection (v1, no ML):** for each pair of categories, compare the
  change in monthly totals across consecutive periods. Flag pairs where one rises
  and the other falls and the magnitudes are within some tolerance (e.g. the
  offsetting amount is ≥60% of the increase). Pure arithmetic over the existing
  JSON — cheap, explainable, no model.
- **Trends / anomalies (v2):** rolling averages and standard-deviation bands per
  category; flag points outside the band.
- **Natural-language summary (v3, optional):** feed the detected patterns (NOT the
  raw transactions) to an LLM to phrase the insight in plain, encouraging language.
  Keep dollar facts deterministic; let the model only handle wording.

## Open questions for later

- What time window makes substitution meaningful — calendar month, trailing 30 days,
  or pay-cycle? (Mortgage and other monthly bills argue for calendar month.)
- How to define "categories that offset each other" — hardcode a few known pairs
  (food-in vs food-out, transport modes) or discover correlated pairs automatically?
- Where does detection run — client-side in the browser over the loaded JSON, or in
  the same 6-hour GitHub Action that writes a precomputed `insights.json`?
- Privacy: anything sent to an LLM should be aggregated category deltas, never
  individual merchants or amounts.

## Why note it now

Capturing this early keeps the data pipeline honest: as long as we keep the
transaction-level `category` on every record (we do), everything above stays
possible later without re-plumbing the data.
