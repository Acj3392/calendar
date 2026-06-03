// Playwright config for the smoke test. The app is a static file served over
// HTTP (Chrome blocks file:// fetch of data/spending.json). No app build step.
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://localhost:8899',
  },
  webServer: {
    command: 'python3 -m http.server 8899',
    url: 'http://localhost:8899/index.html',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
