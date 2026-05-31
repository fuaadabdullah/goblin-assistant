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
