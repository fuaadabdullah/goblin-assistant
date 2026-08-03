import { expect, test } from '@playwright/test';
import { authenticateE2EUser, mockCommonApiRoutes } from './support/common-mocks';

const viewports = [
  { name: 'phone', width: 375, height: 667 },
  { name: 'tablet', width: 768, height: 1024 },
] as const;

const expectNoPageOverflow = async (page: import('@playwright/test').Page) => {
  const dimensions = await page.evaluate(() => ({
    viewportWidth: window.innerWidth,
    documentWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.documentWidth).toBeLessThanOrEqual(dimensions.viewportWidth + 1);
};

for (const viewport of viewports) {
  test.describe(`${viewport.name} viewport`, () => {
    test.use({
      viewport: { width: viewport.width, height: viewport.height },
      hasTouch: true,
      isMobile: viewport.name === 'phone',
    });

    test.beforeEach(async ({ page, context }) => {
      await mockCommonApiRoutes(page);
      await page.route('**/api/auth/validate', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            valid: true,
            user: { id: 'viewport-user', email: 'viewport@example.com', role: 'user' },
            expires_in: 3600,
          }),
        });
      });
      await page.route('**/api/settings/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 1,
              name: 'openai',
              enabled: true,
              models: ['gpt-4o-mini'],
            },
          ]),
        });
      });
      await authenticateE2EUser(context);
    });

    test('login, chat, and settings remain usable without page overflow', async ({ page }) => {
      await page.goto('/login');
      await expect(page.getByLabel(/email/i)).toBeVisible();
      await expect(page.getByLabel(/^password$/i)).toBeVisible();
      await expectNoPageOverflow(page);

      await page.goto('/chat');
      await expect(page.locator('textarea[aria-label="Chat message input"]')).toBeVisible();
      await expectNoPageOverflow(page);

      await page.goto('/settings');
      await expect(page.getByRole('heading', { name: 'Provider & Model Settings' })).toBeVisible();
      await expectNoPageOverflow(page);
    });
  });
}
