// Smoke test — the primary regression guard for the single-file app.
// Loads the app, asserts ZERO console errors, and visits all 4 views x both
// editions (Day / Night), screenshotting each for visual diffing.
const { test, expect } = require('@playwright/test');

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
