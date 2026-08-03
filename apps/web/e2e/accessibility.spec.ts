import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mockCommonApiRoutes } from './support/common-mocks';

const AUTH_COOKIES = [
  { name: 'goblin_auth', value: '1', domain: 'localhost', path: '/' },
  { name: 'goblin_admin', value: '1', domain: 'localhost', path: '/' },
  { name: 'goblin_e2e_auth', value: '1', domain: 'localhost', path: '/' },
  { name: 'goblin_e2e_admin', value: '1', domain: 'localhost', path: '/' },
  { name: 'session_token', value: 'mock-session-token-e2e', domain: 'localhost', path: '/' },
];

const envelope = <T>(data: T) => JSON.stringify({ success: true, data });

async function mockAuditApi(page: import('@playwright/test').Page) {
  await mockCommonApiRoutes(page);

  await page.route('**/api/auth/validate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        valid: true,
        user: { id: 'u-a11y', email: 'a11y@example.com', role: 'admin' },
        expires_in: 3600,
      }),
    });
  });

  await page.route('**/api/v1/health**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: envelope({ overall: 'healthy', timestamp: new Date().toISOString(), services: {} }),
    });
  });

  await page.route('**/api/v1/chat/conversations**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: envelope([]) });
  });

  await page.route('**/api/search/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: envelope({ results: [], collections: [] }),
    });
  });

  await page.route('**/api/settings/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'openai',
          name: 'OpenAI',
          enabled: true,
          configured: true,
          models: ['gpt-4o-mini'],
        },
      ]),
    });
  });

  await page.route('**/api/v1/sandbox/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: envelope([]) });
  });

  await page.route('**/api/v1/account/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: envelope({}) });
  });
}

test.describe('core accessibility audit', () => {
  test.beforeEach(async ({ page, context }) => {
    await mockAuditApi(page);
    await context.addCookies(AUTH_COOKIES);
    await page.addInitScript(() => {
      window.localStorage.setItem(
        'user_data',
        JSON.stringify({ id: 'u-a11y', email: 'a11y@example.com', role: 'admin' })
      );
    });
  });

  for (const route of [
    '/',
    '/chat',
    '/search',
    '/settings',
    '/account',
    '/help',
    '/admin',
    '/admin/logs',
    '/admin/providers',
    '/admin/settings',
    '/onboarding',
    '/sandbox',
  ]) {
    test(`${route} has no automated accessibility violations`, async ({ page }) => {
      await page.goto(route, { waitUntil: 'networkidle' });
      await expect(page.locator('body')).toBeVisible();
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();
      expect(
        results.violations,
        results.violations
          .map((violation) => `${violation.id}: ${violation.help} (${violation.nodes.length})`)
          .join('\n')
      ).toEqual([]);
    });
  }
});
