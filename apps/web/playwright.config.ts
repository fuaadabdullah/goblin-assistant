import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  outputDir: '/Volumes/GOBLINOS 1/goblin-assistant/.playwright/test-results',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    [
      'html',
      {
        outputFolder: '/Volumes/GOBLINOS 1/goblin-assistant/.playwright/html-report',
        open: 'never',
      },
    ],
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: {
    command: 'TMPDIR="/Volumes/GOBLINOS 1/goblin-assistant/.tmp" npm run dev',
    url: 'http://localhost:3000',
    timeout: 180 * 1000,
    reuseExistingServer: !process.env.CI,
  },
});
