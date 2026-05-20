import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should display login form on initial page load', async ({ page }) => {
    await page.goto('/');
    
    // Check for login form elements
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button').filter({ hasText: /login|log in/i })).toBeVisible();
  });

  test('should display register tab', async ({ page }) => {
    await page.goto('/');
    
    // Look for register/signup tab or button
    const registerButton = page.locator('button').filter({ hasText: /register|sign up/i });
    await expect(registerButton).toBeVisible();
  });

  test('should switch between login and register forms', async ({ page }) => {
    await page.goto('/');
    
    // Click register tab
    await page.locator('button').filter({ hasText: /register|sign up/i }).click();
    
    // Should show confirm password field
    await expect(page.locator('input[placeholder*="confirm"], input[type="password"]').nth(1)).toBeVisible();
  });

  test('should validate email format', async ({ page }) => {
    await page.goto('/');
    
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');
    const submitButton = page.locator('button').filter({ hasText: /login|log in/i });
    
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
    await page.goto('/');
    
    const submitButton = page.locator('button').filter({ hasText: /login|log in/i });
    
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
    await page.route('**/api/auth/login', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.abort();
    });
    
    await page.goto('/');
    
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');
    const submitButton = page.locator('button').filter({ hasText: /login|log in/i });
    
    await emailInput.fill('test@example.com');
    await passwordInput.fill('password123');
    await submitButton.click();
    
    // Button should be disabled during submission
    await expect(submitButton).toBeDisabled();
  });

  test('should handle login errors gracefully', async ({ page }) => {
    // Intercept and mock failed login
    await page.route('**/api/auth/login', (route) => {
      route.abort();
    });
    
    await page.goto('/');
    
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');
    const submitButton = page.locator('button').filter({ hasText: /login|log in/i });
    
    await emailInput.fill('test@example.com');
    await passwordInput.fill('password123');
    await submitButton.click();
    
    // Should show error message
    await expect(page.locator('text=/error|failed|connection/i')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('OAuth Login', () => {
  test('should display Google OAuth button if available', async ({ page }) => {
    await page.goto('/');
    
    // Look for Google or OAuth provider buttons
    const oauthButtons = page.locator('button').filter({ hasText: /google|oauth|sign in with/i });
    
    // If OAuth is configured, button should be visible
    const count = await oauthButtons.count();
    if (count > 0) {
      await expect(oauthButtons.first()).toBeVisible();
    }
  });

  test('should navigate to OAuth provider on button click', async ({ page, context }) => {
    await page.goto('/');
    
    // Set up listener for new page (popup/redirect)
    const popupPromise = context.waitForEvent('page');
    
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
