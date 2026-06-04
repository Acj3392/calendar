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
  await page.route('**/data/spending.json', (route) =>
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
  await page.route('**/data/spending.json', (route) =>
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
  await page.route('**/data/spending.json', (route) =>
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

// Net-mode Month header decomposes into Out · In so a net figure can't bury
// gross spend (a paycheck month nets near zero while spend is large). Fixture
// June: out 130, in 2042 -> net inflow +$1912, Out $130, In +$2.0k.
test('Net-mode Month header surfaces Out and In, not just net', async ({ page }) => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures', 'spending.sample.json'), 'utf8');
  await page.route('**/data/spending.json', (route) =>
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
  await page.route('**/data/spending.json', (route) =>
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
