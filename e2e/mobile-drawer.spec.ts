import { test, expect } from '@playwright/test';

test.use({ viewport: { width: 390, height: 844 } });

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
  // click overlay (first fixed inset-0 element)
  const overlay = page.locator('div.fixed.inset-0').first();
  await overlay.click();
  await expect(drawer).toBeHidden();

  // Chat FAB navigates to /chat and focuses composer
  const chatFab = page.getByRole('button', { name: /Open Chat/i });
  await expect(chatFab).toBeVisible();
  await chatFab.click();

  await page.waitForURL(/\/chat/);
  const composer = page.locator('textarea[aria-label="Chat message input"]');
  await expect(composer).toBeVisible();
  await expect(composer).toBeFocused();
});
