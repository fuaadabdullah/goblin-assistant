import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/brutal-release-gate.spec.ts',
  outputDir: './.playwright/brutal-test-results',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [['html', { outputFolder: './.playwright/brutal-html-report', open: 'never' }]],
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
  ],
  webServer: {
    command: 'mkdir -p .tmp && TMPDIR="$PWD/.tmp" pnpm exec next dev',
    url: 'http://localhost:3000',
    timeout: 600 * 1000,
    reuseExistingServer: !process.env.CI,
  },
});
