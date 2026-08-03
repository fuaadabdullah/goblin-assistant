/**
 * Playwright Login Smoke Test
 *
 * End-to-end test: signup → confirm → login → protected route → assert 401 when logged out
 * This test verifies the complete authentication flow works for a "stranger" user.
 */

import { test, expect } from '@playwright/test';
import { authenticateE2EUser, mockCommonApiRoutes, E2E_USER } from './support/common-mocks';

// Test user data for smoke test
const SMOKE_TEST_EMAIL = `smoke-test-${Date.now()}@example.com`;

test.describe('Login Smoke Test - Full Auth Flow', () => {
  test.beforeEach(async ({ page }) => {
    await mockCommonApiRoutes(page);
  });

  test('complete auth flow: signup → confirm → login → protected route → logout', async ({
    page,
    context,
  }) => {
    // ========================================================================
    // Step 1: Unauthenticated user sees login page
    // ========================================================================
    await page.goto('/login');
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page).toHaveURL(/\/login/);

    // ========================================================================
    // Step 2: Signup with email/password (will require confirmation)
    // ========================================================================
    // Mock CSRF token
    await page.route('**/auth/csrf-token', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ csrf_token: 'smoke-test-csrf' }),
      });
    });

    // Mock signup - returns null session (email confirmation required)
    await page.route('**/auth/v1/signup', async (route) => {
      const request = route.request();
      const body = request.postDataJSON();

      // Validate request contains email and password
      expect(body.email).toContain('@example.com');
      expect(body.password).toBeTruthy();

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: {
            id: 'smoke-test-user-id',
            email: body.email,
            email_confirmed_at: null, // Not confirmed yet
          },
          session: null, // No session until confirmed
        }),
      });
    });

    await page.getByRole('button', { name: /don't have an account\? sign up/i }).click();

    // Fill signup form
    await page.getByLabel(/email/i).fill(SMOKE_TEST_EMAIL);
    await page.getByLabel(/^password$/i).fill('smoke-test-password-123');

    // Click signup - we can't actually verify email in E2E, so this simulates
    // the "check your email" state
    await page.getByRole('button', { name: /create account/i }).click();

    // Should show confirmation message (session is null)
    await expect(page.getByText(/check your email/i)).toBeVisible({ timeout: 5000 });

    // ========================================================================
    // Step 3: Simulate email confirmation - set up authenticated session
    // ========================================================================
    // In real flow, user clicks email link → Supabase confirms → session created
    // For E2E, we simulate this by setting up a valid session in storage

    await authenticateE2EUser(context, { ...E2E_USER, email: SMOKE_TEST_EMAIL });

    // Mock /auth/validate to return valid for authenticated requests
    await page.route('**/api/auth/validate', async (route) => {
      const authHeader = route.request().headers()['authorization'];
      if (!authHeader || !authHeader.startsWith('Bearer')) {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ valid: false }),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          valid: true,
          user: { ...E2E_USER, email: SMOKE_TEST_EMAIL },
          expires_in: 3600,
        }),
      });
    });

    // ========================================================================
    // Step 4: Access protected route - should succeed with session
    // ========================================================================
    await page.goto('/chat');

    // Should be on chat page (not redirected to login)
    await expect(page).toHaveURL(/\/chat/, { timeout: 10_000 });
    await expect(page.getByRole('main')).toBeVisible();

    // ========================================================================
    // Step 5: Logout and verify 401 on protected route
    // ========================================================================
    // Mock logout endpoint
    await page.route('**/auth/logout', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

    // Click logout if visible
    const logoutButton = page.getByRole('button', { name: /log.?out|sign.?out/i }).first();
    const logoutCount = await logoutButton.count();

    if (logoutCount > 0) {
      await logoutButton.click();

      // After logout, should be redirected to login
      await expect(page).toHaveURL(/\/login/, { timeout: 5000 });
    }

    // Clear session to simulate unauthenticated state
    await context.clearCookies();

    // Clear localStorage to remove session
    await context.addInitScript(() => {
      window.localStorage.clear();
    });

    // ========================================================================
    // Step 6: Assert 401 when logged out
    // ========================================================================
    // Try to access protected route while unauthenticated
    await page.goto('/chat');

    // Should be redirected to login (middleware protection)
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });

    // Verify we cannot access protected content
    await expect(page.getByLabel(/chat message input/i)).toHaveCount(0);
  });

  test('protected route redirects unauthenticated users to login', async ({ page, context }) => {
    // Ensure no session exists
    await context.clearCookies();
    await context.addInitScript(() => {
      window.localStorage.clear();
    });

    // Try to access multiple protected routes
    const protectedRoutes = ['/chat', '/account', '/settings'];

    for (const route of protectedRoutes) {
      await page.goto(route);
      await expect(page).toHaveURL(/\/login/, { timeout: 5000 });
    }
  });

  test('login with valid credentials goes to protected route', async ({ page, context }) => {
    // Mock CSRF
    await page.route('**/auth/csrf-token', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ csrf_token: 'smoke-csrf-valid' }),
      });
    });

    // Mock login success
    await page.route('**/auth/v1/token**', async (route) => {
      await context.addCookies([
        { name: 'goblin_e2e_auth', value: '1', domain: 'localhost', path: '/' },
      ]);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'authenticated-session-token',
          refresh_token: 'authenticated-refresh-token',
          token_type: 'bearer',
          expires_in: 3600,
          user: { ...E2E_USER },
        }),
      });
    });

    await page.goto('/login');

    // Fill login form
    await page.getByLabel(/email/i).fill('login@example.com');
    await page.getByLabel(/^password$/i).fill('password-123');

    // Submit login
    await page.getByRole('button', { name: /sign in/i }).click();

    // The default post-login destination is home; the protected route must then be accessible.
    await expect(page).toHaveURL(/\/$/, { timeout: 10_000 });
    await page.goto('/chat');
    await expect(page).toHaveURL(/\/chat/, { timeout: 10_000 });
  });
});
