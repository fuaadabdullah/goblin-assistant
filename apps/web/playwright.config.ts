import path from 'node:path';
import { defineConfig, devices } from '@playwright/test';

const workspaceRoot = path.resolve(__dirname, '../..');
const tmpDir = path.join(workspaceRoot, '.tmp');
const browsersPath = path.join(workspaceRoot, '.playwright', 'browsers');
const baseURL = process.env['PLAYWRIGHT_TEST_BASE_URL'] || 'http://localhost:3000';
const shouldStartWebServer = !process.env['PLAYWRIGHT_TEST_BASE_URL'];

export default defineConfig({
  testDir: './e2e',
  outputDir: path.join(workspaceRoot, '.playwright', 'test-results'),
  timeout: process.env['CI'] ? 90_000 : 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 2 : 0,
  workers: 1,
  reporter: [
    [
      'html',
      {
        outputFolder: path.join(workspaceRoot, '.playwright', 'html-report'),
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
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: shouldStartWebServer
    ? {
        command: `TMPDIR="${tmpDir}" PLAYWRIGHT_BROWSERS_PATH="${browsersPath}" npm run dev -- --webpack`,
        url: 'http://localhost:3000',
        timeout: 180 * 1000,
        reuseExistingServer: !process.env['CI'],
      }
    : undefined,
});
