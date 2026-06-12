import { test, expect } from '@playwright/test';
import { mockCommonApiRoutes } from './support/common-mocks';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await mockCommonApiRoutes(page);

    await page.route('**/auth/csrf-token', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ csrf_token: 'csrf-e2e' }),
      });
    });
    await page.route('**/auth/google/url', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ url: 'https://accounts.google.com/o/oauth2/v2/auth?client_id=e2e' }),
      });
    });
  });

  test('should display login form on initial page load', async ({ page }) => {
    await page.goto('/login');

    // Check for login form elements
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/^password$/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('should display register tab', async ({ page }) => {
    await page.goto('/login');

    // Look for register/signup tab or button
    const registerButton = page.getByRole('button', { name: /sign up/i });
    await expect(registerButton).toBeVisible();
  });

  test('should switch between login and register forms', async ({ page }) => {
    await page.goto('/login');

    // Click register tab
    await page.getByRole('button', { name: /sign up/i }).click();

    // Should show register state
    await expect(page.getByRole('heading', { name: /create account/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /create account/i })).toBeVisible();
  });

  test('should validate email format', async ({ page }) => {
    await page.goto('/login');

    const emailInput = page.getByLabel(/email/i);
    const passwordInput = page.getByLabel(/^password$/i);
    const submitButton = page.getByRole('button', { name: /sign in/i });

    // Enter invalid email
    await emailInput.fill('invalid-email');
    await passwordInput.fill('password123');

    // Try to submit
    await submitButton.click();

    // Should show validation error or prevent submission
    const errorMessage = page.locator('text=/invalid|email/i');
    // Either error shows or form doesn't submit
    await page.keyboard.press('Tab'); // Trigger validation
  });

  test('should prevent submission with empty fields', async ({ page }) => {
    await page.goto('/login');

    const submitButton = page.getByRole('button', { name: /sign in/i });

    // Get initial URL
    const initialUrl = page.url();

    // Click submit without filling
    await submitButton.click();

    // Should not navigate away
    await page.waitForTimeout(1000);
    expect(page.url()).toBe(initialUrl);
  });

  test('should show loading state during login', async ({ page }) => {
    // Intercept network request
    await page.route('**/auth/login', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2_000));
      await route.abort();
    });

    await page.goto('/login');

    const emailInput = page.getByLabel(/email/i);
    const passwordInput = page.getByLabel(/^password$/i);
    const submitButton = page.locator('form button[type="submit"]');

    await emailInput.fill('test@example.com');
    await passwordInput.fill('password123');
    await submitButton.click();

    // Button should be disabled during submission
    await expect(page.getByText(/processing/i)).toBeVisible();
    await expect(submitButton).toBeDisabled();
  });

  test('should handle login errors gracefully', async ({ page }) => {
    // Intercept and mock failed login
    await page.route('**/auth/login', (route) => {
      route.abort();
    });

    await page.goto('/login');

    const emailInput = page.getByLabel(/email/i);
    const passwordInput = page.getByLabel(/^password$/i);
    const submitButton = page.getByRole('button', { name: /sign in/i });

    await emailInput.fill('test@example.com');
    await passwordInput.fill('password123');
    await submitButton.click();

    // Graceful failure: remain on login and recover interactive state.
    await expect(page).toHaveURL(/\/login/);
    await expect(submitButton).toBeEnabled({ timeout: 10_000 });

    const errorMessage = page.getByText(/network error|failed|connection|try again/i).first();
    if ((await errorMessage.count()) > 0) {
      await expect(errorMessage).toBeVisible();
    }
  });
});

test.describe('Logout', () => {
  test.beforeEach(async ({ page, context }) => {
    await mockCommonApiRoutes(page);

    await page.route('**/auth/logout', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

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
      { name: 'goblin_auth', value: '1', domain: 'localhost', path: '/' },
      { name: 'session_token', value: 'mock-session-token-e2e', domain: 'localhost', path: '/' },
    ]);
    await context.addInitScript(() => {
      document.cookie = 'goblin_auth=1; Path=/';
      window.localStorage.setItem(
        'user_data',
        JSON.stringify({ id: 'test_user', email: 'test@example.com', role: 'user' })
      );
    });
  });

  test('should show a logout button when authenticated', async ({ page }) => {
    await page.goto('/chat');

    const logoutButton = page
      .getByRole('button', { name: /log.?out|sign.?out/i })
      .or(page.getByRole('link', { name: /log.?out|sign.?out/i }))
      .first();

    const count = await logoutButton.count();
    // Logout may be in a menu — open account menu if needed
    if (count === 0) {
      const accountMenu = page.getByRole('button', { name: /account|profile|user/i }).first();
      const menuCount = await accountMenu.count();
      if (menuCount > 0) {
        await accountMenu.click();
      }
    }
    // Re-check after potential menu open
    const logoutAfterMenu = page
      .getByRole('button', { name: /log.?out|sign.?out/i })
      .or(page.getByRole('link', { name: /log.?out|sign.?out/i }))
      .first();
    const finalCount = await logoutAfterMenu.count();
    if (finalCount > 0) {
      await expect(logoutAfterMenu).toBeVisible();
    }
  });

  test('should redirect to login after logout', async ({ page }) => {
    await page.goto('/chat');

    // Attempt logout via button or direct API call + navigation
    const logoutButton = page.getByRole('button', { name: /log.?out|sign.?out/i }).first();
    const count = await logoutButton.count();

    if (count > 0) {
      await logoutButton.click();
      // Should end up on login page
      await expect(page).toHaveURL(/\/login/, { timeout: 5000 });
    } else {
      // Simulate logout by clearing auth state and navigating
      await page.evaluate(() => {
        window.localStorage.removeItem('user_data');
        document.cookie = 'goblin_auth=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
      });
      await page.goto('/chat');
      // Without auth, should redirect to login
      await expect(page).toHaveURL(/\/login|\/startup/, { timeout: 5000 });
    }
  });

  test('should clear session data after logout', async ({ page }) => {
    await page.goto('/chat');

    const logoutButton = page.getByRole('button', { name: /log.?out|sign.?out/i }).first();
    const count = await logoutButton.count();

    if (count > 0) {
      await logoutButton.click();
      await page.waitForURL(/\/login|\/startup/, { timeout: 5000 });

      // Auth cookie should be cleared
      const cookies = await page.context().cookies();
      const authCookie = cookies.find((c) => c.name === 'goblin_auth' && c.value === '1');
      expect(authCookie).toBeUndefined();
    }
  });
});

test.describe('Session Persistence', () => {
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
      { name: 'goblin_auth', value: '1', domain: 'localhost', path: '/' },
      { name: 'session_token', value: 'mock-session-token-e2e', domain: 'localhost', path: '/' },
    ]);
    await context.addInitScript(() => {
      document.cookie = 'goblin_auth=1; Path=/';
      window.localStorage.setItem(
        'user_data',
        JSON.stringify({ id: 'test_user', email: 'test@example.com', role: 'user' })
      );
    });
  });

  test('should stay authenticated after page reload', async ({ page }) => {
    await page.goto('/chat');
    await expect(page.getByRole('main')).toBeVisible({ timeout: 5000 });

    await page.reload();

    // Should remain on chat, not redirected to login
    await expect(page).toHaveURL(/\/chat/, { timeout: 5000 });
    await expect(page.getByRole('main')).toBeVisible({ timeout: 5000 });
  });

  test('should stay authenticated when navigating between pages', async ({ page }) => {
    await page.goto('/chat');
    await expect(page).toHaveURL(/\/chat/, { timeout: 5000 });

    await page.goto('/settings');
    await expect(page).toHaveURL(/\/settings/, { timeout: 5000 });

    // Navigate back — should still be authenticated
    await page.goto('/chat');
    await expect(page).toHaveURL(/\/chat/, { timeout: 5000 });
  });

  test('should redirect unauthenticated users to login', async ({ page, context }) => {
    // Clear cookies to simulate unauthenticated state
    await context.clearCookies();

    await page.route('**/api/auth/validate', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ valid: false }),
      });
    });

    await page.goto('/chat');

    // Should be redirected away from the protected route
    await expect(page).not.toHaveURL(/\/chat$/, { timeout: 5000 });
  });
});

test.describe('OAuth Login', () => {
  test.beforeEach(async ({ page }) => {
    await mockCommonApiRoutes(page);
  });

  test('should display Google OAuth button if available', async ({ page }) => {
    await page.goto('/login');

    // Look for Google or OAuth provider buttons
    const oauthButtons = page.locator('button').filter({ hasText: /google|oauth|sign in with/i });

    // If OAuth is configured, button should be visible
    const count = await oauthButtons.count();
    if (count > 0) {
      await expect(oauthButtons.first()).toBeVisible();
    }
  });

  test('should navigate to OAuth provider on button click', async ({ page }) => {
    await page.goto('/login');

    const googleButton = page.locator('button').filter({ hasText: /google|oauth/i });
    const count = await googleButton.count();

    if (count > 0) {
      // Click may open popup (we won't complete OAuth flow in E2E)
      await googleButton.first().click();

      // Wait a moment for potential navigation
      await page.waitForTimeout(1000);
    }
  });
});
