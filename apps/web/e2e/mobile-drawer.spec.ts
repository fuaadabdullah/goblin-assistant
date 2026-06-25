import { test, expect } from '@playwright/test';
import { mockCommonApiRoutes } from './support/common-mocks';

test.use({ viewport: { width: 390, height: 844 } });

test.beforeEach(async ({ page, context }) => {
  await mockCommonApiRoutes(page);

  await page.route('**/api/auth/validate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        valid: true,
        user: { id: 'test_user', email: 'test@example.com', role: 'user' },
        expires_in: 3600,
      }),
    });
  });

  await context.addCookies([
    {
      name: 'goblin_auth',
      value: '1',
      domain: 'localhost',
      path: '/',
    },
    {
      name: 'session_token',
      value: 'mock-session-token-e2e',
      domain: 'localhost',
      path: '/',
    },
  ]);

  await context.addInitScript(() => {
    document.cookie = 'goblin_auth=1; Path=/';
    window.localStorage.setItem(
      'user_data',
      JSON.stringify({ id: 'test_user', email: 'test@example.com', role: 'user' })
    );
  });
});

test('mobile drawer opens and closes; Chat FAB navigates to chat', async ({ page }) => {
  await page.goto('/');

  // Open mobile nav
  const openMenu = page.getByRole('button', { name: /Open navigation menu/i });
  await expect(openMenu).toBeVisible();
  await openMenu.click();

  const drawer = page.getByRole('dialog', { name: 'Primary mobile navigation' });
  await expect(drawer).toBeVisible();

  // Dismiss with Escape
  await page.keyboard.press('Escape');
  await expect(drawer).toBeHidden();

  // Reopen and dismiss with overlay click
  await openMenu.click();
  await expect(drawer).toBeVisible();
  // Click an explicit right-side point on the overlay to dismiss the panel.
  const overlay = page.locator('div.fixed.inset-0.bg-black\\/40').first();
  const overlayBox = await overlay.boundingBox();
  if (overlayBox) {
    await page.mouse.click(
      overlayBox.x + Math.max(overlayBox.width - 10, 1),
      overlayBox.y + Math.min(120, Math.max(overlayBox.height - 10, 1))
    );
  }
  await expect(drawer).toBeHidden();

  // Chat FAB navigates to /chat and focuses composer
  const chatFab = page.getByRole('button', { name: /Open Chat/i });
  await expect(chatFab).toBeVisible();
  await chatFab.click();

  await page.waitForURL(/\/chat/);
  const composer = page.locator('textarea[aria-label="Chat message input"]');
  await expect(composer).toBeVisible();
});
