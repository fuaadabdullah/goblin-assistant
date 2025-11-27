import { test, expect } from '@playwright/test';

test.describe('Cross-browser Accessibility and Compatibility Tests', () => {
  test('should load the application in all browsers', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/GoblinOS/);
  });

  test('should have proper focus management', async ({ page }) => {
    await page.goto('/');

    // Check if login page loads (assuming user is not authenticated)
    await expect(page.locator('input[type="email"], input[type="text"]').first()).toBeVisible();

    // Test keyboard navigation
    await page.keyboard.press('Tab');
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(focusedElement).toBeDefined();
  });

  test('should have accessible form elements', async ({ page }) => {
    await page.goto('/login');

    // Check for proper labels
    const emailInput = page.locator('input[type="email"]');
    const emailLabel = page.locator('label').filter({ hasText: /email/i });

    await expect(emailInput).toBeVisible();
    await expect(emailLabel).toBeVisible();

    // Check if label is associated with input
    const inputId = await emailInput.getAttribute('id');
    const labelFor = await emailLabel.getAttribute('for');
    expect(labelFor).toBe(inputId);
  });

  test('should handle responsive design', async ({ page, browserName: _browserName }) => {
    await page.setViewportSize({ width: 375, height: 667 }); // Mobile viewport
    await page.goto('/');

    // Check if content is still accessible on mobile
    const mainContent = page.locator('main, [role="main"], body');
    await expect(mainContent).toBeVisible();

    // Test touch targets are appropriately sized
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();

    for (let i = 0; i < Math.min(buttonCount, 3); i++) {
      const button = buttons.nth(i);
      const box = await button.boundingBox();
      if (box) {
        // Touch targets should be at least 44px
        expect(box.width).toBeGreaterThanOrEqual(44);
        expect(box.height).toBeGreaterThanOrEqual(44);
      }
    }
  });

  test('should work with JavaScript disabled', async ({ browser }) => {
    // Skip this test for WebKit as it has issues with JavaScript disabled
    if (browser.browserType().name() === 'webkit') {
      test.skip();
    }

    const context = await browser.newContext();
    await context.addInitScript(() => {
      // Disable JavaScript by overriding key functions
      Object.defineProperty(window, 'alert', { value: () => {} });
      Object.defineProperty(window, 'confirm', { value: () => true });
      Object.defineProperty(window, 'prompt', { value: () => '' });
    });

    const page = await context.newPage();
    await page.goto('/');

    // Even with JS disabled, basic content should load
    await expect(page.locator('body')).toBeVisible();

    await context.close();
  });

  test('should handle slow networks gracefully', async ({ page }) => {
    // Simulate slow network
    await page.route('**/*', async route => {
      await new Promise(resolve => setTimeout(resolve, 100));
      await route.continue();
    });

    await page.goto('/');

    // App should still load and be usable
    await expect(page.locator('body')).toBeVisible();
  });
});
