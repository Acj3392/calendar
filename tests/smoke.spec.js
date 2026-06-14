// Smoke test — the primary regression guard for the single-file app.
// Loads the app, asserts ZERO console errors, and visits all 4 views x both
// editions (Day / Night), screenshotting each for visual diffing.
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const VIEWS = ['Today', 'Week', 'Month', 'Year'];
// Expected, benign console noise to ignore (inherent to the no-build approach).
const ALLOWED = [/in-browser Babel transformer/i];

test('loads cleanly, no console errors, all views in both editions', async ({ page }) => {
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto('/index.html');
  // App rendered (masthead present) rather than the loading/error fallback.
  await expect(page.getByText('The Daily Spend')).toBeVisible();

  for (const edition of ['Day', 'Night']) {
    await page.locator('button[title="Settings"]').click();
    await page.getByRole('button', { name: edition, exact: true }).click();
    await page.keyboard.press('Escape');
    for (const v of VIEWS) {
      await page.getByRole('button', { name: v, exact: true }).click();
      await page.waitForTimeout(150);
      await page.screenshot({ path: `screenshots/${edition}-${v}.png` });
    }
  }

  // Category filter: toggle a chip, confirm it recomputes without errors, then clear.
  await page.getByRole('button', { name: 'Groceries', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Groceries', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.waitForTimeout(150);
  await page.screenshot({ path: 'screenshots/filtered.png' });
  await page.getByRole('button', { name: 'All', exact: true }).click();
  await expect(page.getByRole('button', { name: 'All', exact: true })).toHaveAttribute('aria-pressed', 'true');

  const real = errors.filter((t) => !ALLOWED.some((re) => re.test(t)));
  expect(real, `Unexpected console errors:\n${real.join('\n')}`).toEqual([]);
});

// Credits render correctly — asserted against the committed fixture (NOT the
// live rolling-window data, which may have no income/refund in range). The
// fixture guarantees a credit day, a refund-offset day, and a pure-income day.
test('credits render and filter against the sample fixture', async ({ page }) => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures', 'spending.sample.json'), 'utf8');
  await page.route('**/data/spending*.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: fixture }));

  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto('/index.html');
  await expect(page.getByText('The Daily Spend')).toBeVisible();

  // Today is the pure-income day: the Payroll credit renders as a teal +$ row,
  // grouped under a "Money in" receipt section (appears in row + subtotal).
  await page.getByRole('button', { name: 'Today', exact: true }).click();
  await expect(page.getByText('+$2000.00', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('Money in', { exact: true })).toBeVisible();

  // A credit-only category chip exists ("+ Income") and filters without errors.
  const incomeChip = page.getByRole('button', { name: '+ Income', exact: true });
  await expect(incomeChip).toBeVisible();
  await incomeChip.click();
  await expect(incomeChip).toHaveAttribute('aria-pressed', 'true');
  await page.waitForTimeout(150);
  await page.screenshot({ path: 'screenshots/credits-fixture.png' });

  // A category that has BOTH debits and credits (Groceries: spend + a return)
  // must NOT spawn a redundant "+ Groceries" credit chip — the debit chip
  // already filters it. Only its debit chip should exist.
  await expect(page.getByRole('button', { name: 'Groceries', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '+ Groceries', exact: true })).toHaveCount(0);

  const real = errors.filter((t) => !ALLOWED.some((re) => re.test(t)));
  expect(real, `Unexpected console errors:\n${real.join('\n')}`).toEqual([]);
});

// Focus mode: filtering reframes the view around the slice. With Coffee Shops
// selected, 06-01 has coffee spend (figure) while 06-02 (other spend) and 06-03
// (income only) have none (recede). The Focus strip + reframed header are the
// unmistakable "you are filtered" signal the feature exists to provide.
test('filtering engages Focus mode — strip + reframed header', async ({ page }) => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures', 'spending.sample.json'), 'utf8');
  await page.route('**/data/spending*.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: fixture }));

  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto('/index.html');
  await expect(page.getByText('The Daily Spend')).toBeVisible();

  // Unfiltered: the Month section reads its default masthead.
  await page.getByRole('button', { name: 'Month', exact: true }).click();
  await expect(page.getByText('The Month in Full')).toBeVisible();

  // Filter to Coffee Shops → Focus strip names the slice, header reframes.
  await page.getByRole('button', { name: 'Coffee Shops', exact: true }).click();
  await expect(page.getByText('Focus · Coffee Shops')).toBeVisible();
  await expect(page.getByText('Coffee Shops · The Month')).toBeVisible();
  await expect(page.getByText('The Month in Full')).toHaveCount(0);
  await page.screenshot({ path: 'screenshots/focus-mode.png' });

  // Tapping All clears the filter and restores the default masthead.
  await page.getByRole('button', { name: 'All', exact: true }).click();
  await expect(page.getByText('The Month in Full')).toBeVisible();

  const real = errors.filter((t) => !ALLOWED.some((re) => re.test(t)));
  expect(real, `Unexpected console errors:\n${real.join('\n')}`).toEqual([]);
});

// Focus fill = category spend ONLY. With Restaurants & Bars filtered, only the
// spend days (06-01 $40, 06-04 $200) carry a verdict fill; the refund-only day
// (06-03) and the empty in-range day (06-05) recede to a transparent cell. The
// refund day keeps its faint "+" marker. Guards against the lime "good" wash
// leaking onto zero-spend days.
test('Focus mode fills only category-spend days; zero-spend days recede', async ({ page }) => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures', 'focus.sample.json'), 'utf8');
  await page.route('**/data/spending*.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: fixture }));

  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto('/index.html');
  await expect(page.getByText('The Daily Spend')).toBeVisible();
  await page.getByRole('button', { name: 'Month', exact: true }).click();

  // Filter to the category.
  await page.getByRole('button', { name: 'Restaurants & Bars', exact: true }).click();
  await expect(page.getByText('Focus · Restaurants & Bars')).toBeVisible();

  const TRANSPARENT = 'rgba(0, 0, 0, 0)';
  const bg = (ds) => page.locator(`[data-day="${ds}"]`)
    .evaluate((el) => getComputedStyle(el).backgroundColor);

  // Spend days are filled; zero-spend days (refund-only, empty in-range) recede.
  expect(await bg('2026-06-01'), 'spend day $40 should be filled').not.toBe(TRANSPARENT);
  expect(await bg('2026-06-04'), 'spend day $200 should be filled').not.toBe(TRANSPARENT);
  expect(await bg('2026-06-03'), 'refund-only day should recede').toBe(TRANSPARENT);
  expect(await bg('2026-06-05'), 'empty in-range day should recede').toBe(TRANSPARENT);
  // The other-category day (Groceries) also recedes under a Restaurants filter.
  expect(await bg('2026-06-02'), 'other-category day should recede').toBe(TRANSPARENT);

  // Spend days carry the right verdict, not just any fill: 06-01 ($40, under the
  // $120 avg) reads "met goal ✓"; 06-04 ($200, over) reads "overspent ▲".
  await expect(page.locator('[data-day="2026-06-01"]').getByText('$40')).toBeVisible();
  await expect(page.locator('[data-day="2026-06-01"]').getByText('✓')).toBeVisible();
  await expect(page.locator('[data-day="2026-06-04"]').getByText('$200')).toBeVisible();
  await expect(page.locator('[data-day="2026-06-04"]').getByText('▲')).toBeVisible();

  // The refund-only day keeps its faint "+" money-in marker.
  await expect(page.locator('[data-day="2026-06-03"]').getByText('+', { exact: true })).toBeVisible();

  await page.screenshot({ path: 'screenshots/focus-spend-only.png' });

  const real = errors.filter((t) => !ALLOWED.some((re) => re.test(t)));
  expect(real, `Unexpected console errors:\n${real.join('\n')}`).toEqual([]);
});

// Validation guards the load-bearing field: every total/verdict is recomputed
// from tx.amount, so a non-numeric amount must fail loudly (error card) rather
// than silently render "$NaN". Guards the otherwise-uncovered failure path.
test('rejects non-numeric tx.amount with a clear error card, not $NaN', async ({ page }) => {
  const bad = JSON.stringify({
    today: '2026-06-03',
    data: [{ date: '2026-06-01', total: 10, transactions: [
      { merchant: 'Mystery', amount: 'oops', category: 'Groceries', type: 'debit' },
    ] }],
  });
  await page.route('**/data/spending*.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: bad }));

  await page.goto('/index.html');
  await expect(page.getByText(/Couldn't load spending data/)).toBeVisible();
  await expect(page.getByText(/non-numeric amount/)).toBeVisible();
  // The app must NOT render the calendar with bad data.
  await expect(page.getByText('The Daily Spend')).toHaveCount(0);
});

// Net-mode Month header decomposes into Out · In so a net figure can't bury
// gross spend (a paycheck month nets near zero while spend is large). Fixture
// June: out 130, in 2042 -> net inflow +$1912, Out $130, In +$2.0k.
test('Net-mode Month header surfaces Out and In, not just net', async ({ page }) => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures', 'spending.sample.json'), 'utf8');
  await page.route('**/data/spending*.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: fixture }));

  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto('/index.html');
  await expect(page.getByText('The Daily Spend')).toBeVisible();

  // Flip to Net mode.
  await page.locator('button[title="Settings"]').click();
  await page.getByRole('button', { name: 'Net', exact: true }).click();
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Month', exact: true }).click();

  // The net headline alone (+$1912) would read as near-zero spend; the Out/In
  // decomposition makes the $130 gross spend and $2042 money-in explicit.
  await expect(page.getByText('+$1912')).toBeVisible();
  await expect(page.getByText(/Out\s*\$130/)).toBeVisible();
  await expect(page.getByText(/In\s*\+\$2\.0k/)).toBeVisible();
  await page.screenshot({ path: 'screenshots/net-month-decomp.png' });

  const real = errors.filter((t) => !ALLOWED.some((re) => re.test(t)));
  expect(real, `Unexpected console errors:\n${real.join('\n')}`).toEqual([]);
});

// Net-verdict toggle (PR2): flipping the basis re-reads the verdict as net.
// Today in the fixture is a pure-income day (total 0, received 2000): spend
// mode reads "No spend", net mode reads "Net positive".
test('verdict-basis toggle flips Today between No spend and Net positive', async ({ page }) => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures', 'spending.sample.json'), 'utf8');
  await page.route('**/data/spending*.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: fixture }));

  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto('/index.html');
  await page.getByRole('button', { name: 'Today', exact: true }).click();

  // Default = spend mode: pure-income day's verdict stamp reads "No spend ●".
  await expect(page.getByText('No spend ●')).toBeVisible();

  // Flip to Net in Settings.
  await page.locator('button[title="Settings"]').click();
  await page.getByRole('button', { name: 'Net', exact: true }).click();
  await page.keyboard.press('Escape');

  // Now the same day reads net-positive.
  await expect(page.getByText('Net positive', { exact: false })).toBeVisible();
  await page.screenshot({ path: 'screenshots/net-mode.png' });

  const real = errors.filter((t) => !ALLOWED.some((re) => re.test(t)));
  expect(real, `Unexpected console errors:\n${real.join('\n')}`).toEqual([]);
});

// ── "Not applicable" categories (user-hidden from totals) ─────────────────────
// Hiding a category in Settings must drop it from every total/verdict, remove its
// filter chip, persist across reload, and restore cleanly when un-hidden. Fixture
// Today (06-04) = Mortgage $500 + Coffee $20; hiding Mortgage drops the headline
// from $520 to $20. Hide-toggle buttons are named "Hide/Show <cat>" so they don't
// collide with the filter chip "<cat>".
test('hidden categories drop from totals, hide their chip, and persist', async ({ page }) => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures', 'exclude.sample.json'), 'utf8');
  await page.route('**/data/spending*.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: fixture }));

  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto('/index.html');
  await page.getByRole('button', { name: 'Today', exact: true }).click();

  // Baseline: Today headline = $520, and a Mortgage filter chip exists.
  await expect(page.getByText('$520', { exact: false }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Mortgage', exact: true })).toBeVisible();

  // Hide Mortgage via the Settings "Hide categories" toggle.
  await page.locator('button[title="Settings"]').click();
  await page.getByRole('button', { name: 'Hide Mortgage' }).click();
  await page.keyboard.press('Escape');

  // Headline drops to $20; the Mortgage chip is gone from the filter bar.
  await expect(page.getByText('$20', { exact: false }).first()).toBeVisible();
  await expect(page.getByText('$520', { exact: false })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Mortgage', exact: true })).toHaveCount(0);
  await page.screenshot({ path: 'screenshots/hidden-categories.png' });

  // Persists across reload (route stays registered through reload).
  await page.reload();
  await page.getByRole('button', { name: 'Today', exact: true }).click();
  await expect(page.getByText('$20', { exact: false }).first()).toBeVisible();

  // Un-hiding restores the full total.
  await page.locator('button[title="Settings"]').click();
  await page.getByRole('button', { name: 'Show Mortgage' }).click();
  await page.keyboard.press('Escape');
  await expect(page.getByText('$520', { exact: false }).first()).toBeVisible();

  const real = errors.filter((t) => !ALLOWED.some((re) => re.test(t)));
  expect(real, `Unexpected console errors:\n${real.join('\n')}`).toEqual([]);
});

// Hidden transactions stay VISIBLE (muted) in the day's receipt under a
// "Not applicable" heading, but don't count toward the subtotal. Day 06-02 =
// Coffee $50 (counted) + Mortgage debit $200 + Mortgage credit $200 (both hidden).
// With Mortgage hidden the day's only non-excluded credit is gone, so the receipt
// takes the flat (received === 0) path — the riskiest one to get right.
test('hidden transactions listed muted under "Not applicable", uncounted', async ({ page }) => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures', 'exclude.sample.json'), 'utf8');
  await page.route('**/data/spending*.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: fixture }));

  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto('/index.html');
  await expect(page.getByText('The Daily Spend')).toBeVisible();

  // Hide Mortgage.
  await page.locator('button[title="Settings"]').click();
  await page.getByRole('button', { name: 'Hide Mortgage' }).click();
  await page.keyboard.press('Escape');

  // Open 06-02 in the Month grid (June is the default month for a 06-04 "today").
  await page.getByRole('button', { name: 'Month', exact: true }).click();
  await page.locator('[data-day="2026-06-02"]').click();

  // Day headline counts only Coffee → $50.00, NOT $250 (Mortgage excluded).
  await expect(page.getByText('$50.00').first()).toBeVisible();
  // The hidden Mortgage transactions are still listed, under "Not applicable".
  await expect(page.getByText('Not applicable')).toBeVisible();
  await expect(page.getByText('Escrow Refund')).toBeVisible();
  await page.screenshot({ path: 'screenshots/not-applicable-receipt.png' });

  const real = errors.filter((t) => !ALLOWED.some((re) => re.test(t)));
  expect(real, `Unexpected console errors:\n${real.join('\n')}`).toEqual([]);
});

// A single global reminder ("N categories hidden") sits below the filter bar so
// the user knows the figures are partial. It's absent when nothing is hidden, and
// tapping it opens Settings to manage the hidden set.
test('HiddenNote shows the count and opens Settings; absent when none hidden', async ({ page }) => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures', 'exclude.sample.json'), 'utf8');
  await page.route('**/data/spending*.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: fixture }));

  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto('/index.html');
  await expect(page.getByText('The Daily Spend')).toBeVisible();

  // Nothing hidden → no note.
  await expect(page.getByText(/categor(y|ies) hidden/i)).toHaveCount(0);

  // Hide Mortgage → a "1 category hidden" note appears.
  await page.locator('button[title="Settings"]').click();
  await page.getByRole('button', { name: 'Hide Mortgage' }).click();
  await page.keyboard.press('Escape');

  const note = page.getByRole('button', { name: /1 category hidden/i });
  await expect(note).toBeVisible();
  await page.screenshot({ path: 'screenshots/hidden-note.png' });

  // Tapping it re-opens Settings (the "Show Mortgage" toggle proves the popover is open).
  await note.click();
  await expect(page.getByRole('button', { name: 'Show Mortgage' })).toBeVisible();

  const real = errors.filter((t) => !ALLOWED.some((re) => re.test(t)));
  expect(real, `Unexpected console errors:\n${real.join('\n')}`).toEqual([]);
});

// Category budget goal (Focus mode): focusing a category with a Monarch budget shows
// "$spent of $budget · status" in the view header, colored by over/under the FULL
// budget (not the prorated pace line). Fixture pins today = day 15 of June (30 days),
// so the pace target is budget × 0.5. Restaurants $120 (under pace) → on track;
// Coffee $80 vs $100 budget but >$50 pace → ahead of pace (still NOT rust);
// Shopping $320 vs $200 → over budget (rust); Groceries has no budget → relative fallback.
test('budget goal: header shows $spent of $budget with full-budget color states', async ({ page }) => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures', 'budget.sample.json'), 'utf8');
  await page.route('**/data/spending*.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: fixture }));

  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto('/index.html');
  await expect(page.getByText('The Daily Spend')).toBeVisible();
  await page.getByRole('button', { name: 'Month', exact: true }).click();

  // Restaurants: $120 spent, $300 budget, under the $150 pace → "on track".
  await page.getByRole('button', { name: 'Restaurants & Bars', exact: true }).click();
  await expect(page.getByText('$120 of $300')).toBeVisible();
  await expect(page.getByText('on track')).toBeVisible();
  // Replace-not-stack: the relative "vs avg" strip text is gone when a budget shows.
  await expect(page.getByText(/judged vs .*\/day avg/)).toHaveCount(0);
  await page.screenshot({ path: 'screenshots/budget-on-track.png' });
  await page.getByRole('button', { name: 'All', exact: true }).click();

  // Coffee: $80 spent, $100 budget — over the $50 pace but UNDER budget → "ahead of
  // pace" and NOT flagged over-budget (the false-alarm guard).
  await page.getByRole('button', { name: 'Coffee Shops', exact: true }).click();
  await expect(page.getByText('$80 of $100')).toBeVisible();
  await expect(page.getByText('ahead of pace')).toBeVisible();
  await expect(page.getByText('over budget')).toHaveCount(0);
  await page.getByRole('button', { name: 'All', exact: true }).click();

  // Shopping: $320 spent, $200 budget → "over budget".
  await page.getByRole('button', { name: 'Shopping', exact: true }).click();
  await expect(page.getByText('$320 of $200')).toBeVisible();
  await expect(page.getByText('over budget')).toBeVisible();
  await page.screenshot({ path: 'screenshots/budget-over.png' });
  await page.getByRole('button', { name: 'All', exact: true }).click();

  // Groceries: no budget → no budget line. (In Month view the relative "vs avg" strip
  // text is intentionally hidden too, so a no-budget category shows neither line.)
  await page.getByRole('button', { name: 'Groceries', exact: true }).click();
  await expect(page.getByText(/of \$/)).toHaveCount(0);
  await expect(page.getByText(/judged vs .*\/day avg/)).toHaveCount(0);
  await page.getByRole('button', { name: 'All', exact: true }).click();

  // Today view shows the same month budget line for the focused category.
  await page.getByRole('button', { name: 'Today', exact: true }).click();
  await page.getByRole('button', { name: 'Restaurants & Bars', exact: true }).click();
  await expect(page.getByText('$120 of $300')).toBeVisible();

  const real = errors.filter((t) => !ALLOWED.some((re) => re.test(t)));
  expect(real, `Unexpected console errors:\n${real.join('\n')}`).toEqual([]);
});

// Budget basis follows the Spend/Net toggle: money-in (refunds, reimbursements) in a
// category offsets its cost against budget. Restaurants = $120 spent − $40 Venmo
// split = $80 net of $300. Spend mode shows gross $120; Net mode shows net $80.
test('budget line uses NET (money-in offsets the category) when in Net mode', async ({ page }) => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures', 'budget.sample.json'), 'utf8');
  await page.route('**/data/spending*.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: fixture }));

  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto('/index.html');
  await expect(page.getByText('The Daily Spend')).toBeVisible();
  await page.getByRole('button', { name: 'Month', exact: true }).click();
  await page.getByRole('button', { name: 'Restaurants & Bars', exact: true }).click();

  // Spend mode (default): gross $120 of $300.
  await expect(page.getByText('$120 of $300')).toBeVisible();

  // Flip to Net mode → the $40 refund offsets it → $80 of $300.
  await page.locator('button[title="Settings"]').click();
  await page.getByRole('button', { name: 'Net', exact: true }).click();
  await page.keyboard.press('Escape');
  await expect(page.getByText('$80 of $300')).toBeVisible();
  await expect(page.getByText('$120 of $300')).toHaveCount(0);

  const real = errors.filter((t) => !ALLOWED.some((re) => re.test(t)));
  expect(real, `Unexpected console errors:\n${real.join('\n')}`).toEqual([]);
});

// Edge + rollup propagation: 06-03's ONLY transaction is Mortgage $1000. Unfiltered
// it reads "overspent ▲"; once Mortgage is hidden the day has no applicable activity
// and must read "No spend ●" (not blank/error). And the Year total must drop from
// $2670 to $170 — proving exclusion reaches the annual rollup, not just the headline.
test('only-excluded day reads "No spend ●"; exclusion reaches the Year rollup', async ({ page }) => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures', 'exclude.sample.json'), 'utf8');
  await page.route('**/data/spending*.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: fixture }));

  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto('/index.html');
  await expect(page.getByText('The Daily Spend')).toBeVisible();

  // Year baseline = $2670 (900 + 250 + 1000 + 520).
  await page.getByRole('button', { name: 'Year', exact: true }).click();
  await expect(page.getByText('$2670')).toBeVisible();

  // Month baseline: 06-03 (Mortgage $1000 only) reads overspent ▲.
  await page.getByRole('button', { name: 'Month', exact: true }).click();
  const cell = page.locator('[data-day="2026-06-03"]');
  await expect(cell.getByText('▲')).toBeVisible();

  // Hide Mortgage.
  await page.locator('button[title="Settings"]').click();
  await page.getByRole('button', { name: 'Hide Mortgage' }).click();
  await page.keyboard.press('Escape');

  // 06-03 now reads "No spend ●", not ▲ (its only activity was hidden).
  await expect(cell.getByText('●')).toBeVisible();
  await expect(cell.getByText('▲')).toHaveCount(0);

  // Year rollup drops to $170 (100 + 50 + 0 + 20) — exclusion reached the annual sum.
  await page.getByRole('button', { name: 'Year', exact: true }).click();
  await expect(page.getByText('$170').first()).toBeVisible();
  await expect(page.getByText('$2670')).toHaveCount(0);

  const real = errors.filter((t) => !ALLOWED.some((re) => re.test(t)));
  expect(real, `Unexpected console errors:\n${real.join('\n')}`).toEqual([]);
});

// Data-mode toggle: the app defaults to the Fake Data Prototype (safe to share).
// Picking "Personal App" requires the passcode; a wrong code is rejected, the
// correct code switches to the live-data view.
test('mode toggle defaults to fake and gates Personal App behind the passcode', async ({ page }) => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures', 'spending.sample.json'), 'utf8');
  await page.route('**/data/spending*.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: fixture }));

  await page.goto('/index.html');
  await expect(page.getByText('The Daily Spend')).toBeVisible();

  // Default: fake mode — both the badge and the active toggle say so.
  await expect(page.getByText(/Demo data/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Fake Data Prototype' })).toBeVisible();

  // Click Personal App → inline passcode field appears.
  await page.getByRole('button', { name: /Personal App/ }).click();
  const pw = page.getByPlaceholder('Password');
  await expect(pw).toBeVisible();

  // Wrong passcode is rejected, stays in fake mode.
  await pw.fill('nope');
  await page.getByRole('button', { name: 'Unlock', exact: true }).click();
  await expect(page.getByText('Incorrect')).toBeVisible();
  await expect(page.getByText(/Demo data/)).toBeVisible();

  // Correct passcode unlocks and switches to Personal — live data.
  await pw.fill('Rosebud23!');
  await page.getByRole('button', { name: 'Unlock', exact: true }).click();
  await expect(page.getByText(/Personal — live data/)).toBeVisible();
});
