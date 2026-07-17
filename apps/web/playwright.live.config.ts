import path from 'node:path';
import { defineConfig, devices } from '@playwright/test';

const workspaceRoot = path.resolve(__dirname, '../..');
const baseURL = process.env['PLAYWRIGHT_TEST_BASE_URL'] || 'http://localhost:3000';

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/auth-live-smoke.spec.ts',
  outputDir: path.join(workspaceRoot, '.playwright', 'live-test-results'),
  timeout: process.env['CI'] ? 90_000 : 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 1 : 0,
  workers: 1,
  reporter: [
    [
      'html',
      {
        outputFolder: path.join(workspaceRoot, '.playwright', 'live-html-report'),
        open: 'never',
      },
    ],
  ],
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: undefined,
});
