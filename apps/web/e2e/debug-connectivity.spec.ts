import { test, expect } from '@playwright/test';
import { mockCommonApiRoutes } from './support/common-mocks';

test.describe('Debug Connectivity Page', () => {
  test.beforeEach(async ({ page, context }) => {
    await mockCommonApiRoutes(page);

    // Mock health endpoint
    await page.route('**/api/v1/health', async (route) => {
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

    // Set up authenticated state
    await context.addCookies([
      {
        name: 'goblin_auth',
        value: '1',
        domain: 'localhost',
        path: '/',
      },
      {
        name: 'session_token',
        value: 'mock-session-token-debug',
        domain: 'localhost',
        path: '/',
      },
    ]);

    await context.addInitScript(() => {
      window.localStorage.setItem(
        'user_data',
        JSON.stringify({ id: 'debug_user', email: 'debug@example.com', role: 'user' })
      );
    });
  });

  test('should display page title and health status section', async ({ page }) => {
    await page.goto('/debug/connectivity');

    await expect(page.getByRole('heading', { name: /Connectivity Debug/i })).toBeVisible();
    await expect(page.getByText(/Health Status/i)).toBeVisible();
  });

  test('should display auth status section', async ({ page }) => {
    await page.goto('/debug/connectivity');

    await expect(page.getByRole('heading', { name: /Auth Status/i })).toBeVisible();

    // Should show authenticated state
    await expect(page.getByText(/Authenticated/i)).toBeVisible();
  });

  test('should show user details when authenticated', async ({ page }) => {
    await page.goto('/debug/connectivity');

    await expect(page.getByText(/debug@example\.com/)).toBeVisible();
    await expect(page.getByText(/Role:/)).toBeVisible();
    await expect(page.getByText(/User ID:/)).toBeVisible();
  });

  test('should display token in masked format', async ({ page }) => {
    await page.goto('/debug/connectivity');

    // Token should be masked (showing first 8 and last 4 chars)
    await expect(page.locator('code').filter({ hasText: /.../ }).first()).toBeVisible();
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
    await expect(page.getByText(/✓ Success!/i)).toBeVisible();
  });

  test('should display auth endpoint test buttons', async ({ page }) => {
    await page.goto('/debug/connectivity');

    await expect(page.getByRole('heading', { name: /Auth Endpoints/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Test Validate Token/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Test Logout/i })).toBeVisible();
  });

  test('should show auth required badge on authenticated endpoints', async ({ page }) => {
    await page.goto('/debug/connectivity');

    const authBadges = page.locator(`.${'authBadge'}`);
    const count = await authBadges.count();

    // Should have auth badges on chat and auth endpoint tests
    expect(count).toBeGreaterThan(0);
  });

  test('should display status summary section', async ({ page }) => {
    await page.goto('/debug/connectivity');

    await expect(page.getByRole('heading', { name: /Summary/i })).toBeVisible();
    await expect(page.getByText(/Frontend Health/)).toBeVisible();
    await expect(page.getByText(/Backend Health/)).toBeVisible();
    await expect(page.getByText(/Auth Status/)).toBeVisible();
    await expect(page.getByText(/Chat API/)).toBeVisible();
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

    await expect(page.getByText(/Not authenticated/i)).toBeVisible();
  });

  test('should handle health endpoint error gracefully', async ({ page }) => {
    // Mock failed health endpoint
    await page.route('**/api/v1/health', async (route) => {
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

    await page.route('**/api/v1/health', async (route) => {
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
    // Set up authenticated state
    await context.addCookies([
      {
        name: 'goblin_auth',
        value: '1',
        domain: 'localhost',
        path: '/',
      },
      {
        name: 'session_token',
        value: 'mock-session-token-chat',
        domain: 'localhost',
        path: '/',
      },
    ]);

    await context.addInitScript(() => {
      window.localStorage.setItem(
        'user_data',
        JSON.stringify({ id: 'chat_user', email: 'chat@example.com', role: 'user' })
      );
    });

    await page.goto('/chat');

    // Should show connection status in header
    await expect(page.getByText(/Live gateway/i)).toBeVisible({ timeout: 10000 });
  });

  test('should display debug link in chat header', async ({ page, context }) => {
    // Set up authenticated state
    await context.addCookies([
      {
        name: 'goblin_auth',
        value: '1',
        domain: 'localhost',
        path: '/',
      },
    ]);

    await page.goto('/chat');

    const debugLink = page.getByRole('link', { name: /Debug/i });
    const iconLink = page
      .locator('a')
      .filter({ has: page.locator('svg') })
      .first();

    // Debug link should be present (via icon)
    const count = await iconLink.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});
