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

  // A credit category chip exists ("+ Income") and filters without errors.
  const incomeChip = page.getByRole('button', { name: '+ Income', exact: true });
  await expect(incomeChip).toBeVisible();
  await incomeChip.click();
  await expect(incomeChip).toHaveAttribute('aria-pressed', 'true');
  await page.waitForTimeout(150);
  await page.screenshot({ path: 'screenshots/credits-fixture.png' });

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
