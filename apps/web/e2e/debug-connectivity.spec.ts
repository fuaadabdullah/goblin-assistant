import { test, expect } from '@playwright/test';
import { authenticateE2EUser, mockCommonApiRoutes } from './support/common-mocks';

test.describe('Debug Connectivity Page', () => {
  test.beforeEach(async ({ page, context }) => {
    await mockCommonApiRoutes(page);
    await authenticateE2EUser(context);

    // Mock health endpoint
    await page.route('**/api/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          overall: 'healthy',
          timestamp: new Date().toISOString(),
          services: {
            api: { status: 'healthy' },
            database: { status: 'healthy' },
            cache: { status: 'healthy' },
          },
        }),
      });
    });

    // Mock chat conversations endpoint
    await page.route('**/chat/conversations', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          conversation_id: 'conv-debug-test',
          title: 'Test conversation',
          created_at: new Date().toISOString(),
        }),
      });
    });

    // Mock auth validate endpoint
    await page.route('**/api/auth/validate', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          valid: true,
          user: { id: 'debug_user', email: 'debug@example.com', role: 'user' },
          expires_in: 3600,
        }),
      });
    });

    await context.addCookies([
      { name: 'goblin_e2e_admin', value: '1', domain: 'localhost', path: '/' },
    ]);
  });

  test('should display page title and health status section', async ({ page }) => {
    await page.goto('/debug/connectivity');

    await expect(page.getByRole('heading', { name: /Connectivity Debug/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Health Status' })).toBeVisible();
  });

  test('should display auth status section', async ({ page }) => {
    await page.goto('/debug/connectivity');

    await expect(page.getByRole('heading', { name: /Auth Status/i })).toBeVisible();

    // Should show authenticated state
    await expect(page.getByText(/Authenticated/i).first()).toBeVisible();
  });

  test('should show user details when authenticated', async ({ page }) => {
    await page.goto('/debug/connectivity');

    await expect(page.getByText(/test@example\.com/)).toBeVisible();
    await expect(page.getByText(/Role:/)).toBeVisible();
    await expect(page.getByText(/User ID:/)).toBeVisible();
  });

  test('should not expose the session token', async ({ page }) => {
    await page.goto('/debug/connectivity');

    await expect(page.locator('code')).toHaveCount(0);
  });

  test('should have chat endpoint test button', async ({ page }) => {
    await page.goto('/debug/connectivity');

    const testButton = page.getByRole('button', { name: /Test Fetch Conversations/i });
    await expect(testButton).toBeVisible();
  });

  test('should fetch conversations successfully', async ({ page }) => {
    await page.goto('/debug/connectivity');

    const testButton = page.getByRole('button', { name: /Test Fetch Conversations/i });
    await testButton.click();

    // Should show success message
    await expect(page.getByText(/✓ Success!/i).first()).toBeVisible();
  });

  test('should display auth endpoint test buttons', async ({ page }) => {
    await page.goto('/debug/connectivity');

    await expect(page.getByRole('heading', { name: /Auth Endpoints/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Test Validate Token/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Test Logout/i })).toBeVisible();
  });

  test('should show auth required badge on authenticated endpoints', async ({ page }) => {
    await page.goto('/debug/connectivity');

    const authBadges = page.getByText('Auth Required', { exact: true });
    const count = await authBadges.count();

    // Should have auth badges on chat and auth endpoint tests
    expect(count).toBeGreaterThan(0);
  });

  test('should display status summary section', async ({ page }) => {
    await page.goto('/debug/connectivity');

    const summary = page.getByRole('heading', { name: /Summary/i }).locator('..');
    await expect(summary.getByText(/Frontend Health/)).toBeVisible();
    await expect(summary.getByText(/Backend Health/)).toBeVisible();
    await expect(summary.getByText(/Auth Status/)).toBeVisible();
    await expect(summary.getByText(/Chat API/)).toBeVisible();
  });

  test('should show not authenticated when no auth', async ({ page, context }) => {
    // Clear auth state
    await context.clearCookies();
    await page.route('**/api/auth/validate', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ valid: false }),
      });
    });

    await page.goto('/debug/connectivity');

    await expect(page).toHaveURL(/\/login/);
  });

  test('should handle health endpoint error gracefully', async ({ page }) => {
    // Mock failed health endpoint
    await page.route('**/api/health', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Health check failed' }),
      });
    });

    await page.goto('/debug/connectivity');

    // Page should still render with error message
    await expect(page.getByRole('heading', { name: /Connectivity Debug/i })).toBeVisible();
  });
});

test.describe('Connection Status Indicator', () => {
  test.beforeEach(async ({ page }) => {
    await mockCommonApiRoutes(page);

    await page.route('**/api/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          overall: 'healthy',
          timestamp: new Date().toISOString(),
          services: {
            api: { status: 'healthy' },
          },
        }),
      });
    });
  });

  test('should display healthy status in chat header', async ({ page, context }) => {
    await authenticateE2EUser(context);

    await page.goto('/chat');

    // Should show connection status in header
    await expect(page.getByText(/Live gateway/i)).toBeVisible({ timeout: 10000 });
  });

  test('should display debug link in chat header', async ({ page, context }) => {
    await authenticateE2EUser(context, {
      id: 'admin_user',
      email: 'admin@example.com',
      role: 'admin',
      created_at: '2026-01-01T00:00:00.000Z',
      user_metadata: { name: 'E2E Admin' },
    });

    await page.goto('/chat');

    await expect(page.getByTitle('Debug connectivity')).toBeVisible();
  });
});
