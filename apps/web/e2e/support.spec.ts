import { expect, test } from '@playwright/test';
import { mockCommonApiRoutes } from './support/common-mocks';

const AUTH_COOKIES = [
  { name: 'goblin_auth', value: '1', domain: 'localhost', path: '/' },
  { name: 'session_token', value: 'mock-session-token-e2e', domain: 'localhost', path: '/' },
];

const AUTH_INIT_SCRIPT = () => {
  document.cookie = 'goblin_auth=1; Path=/';
  window.localStorage.setItem(
    'user_data',
    JSON.stringify({ id: 'test_user', email: 'test@example.com', role: 'user' })
  );
};

test.describe('Help: Support submission', () => {
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

    await context.addCookies(AUTH_COOKIES);
    await context.addInitScript(AUTH_INIT_SCRIPT);
  });

  test('submits a support message and shows confirmation', async ({ page }) => {
    let submittedMessage = '';

    await page.route('**/api/v1/support/message*', async (route) => {
      const payload = route.request().postDataJSON() as { message?: string };
      submittedMessage = payload.message ?? '';

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'ticket-e2e',
            status: 'received',
            timestamp: new Date().toISOString(),
          },
        }),
      });
    });

    await page.goto('/help');
    await page.getByPlaceholder('Tell us what you need help with...').fill('My account is stuck');
    await page.getByRole('button', { name: /send to support/i }).click();

    await expect(page.getByText('Message sent.')).toBeVisible({ timeout: 5000 });
    expect(submittedMessage).toBe('My account is stuck');
  });

  test('surfaces an error when support submission fails', async ({ page }) => {
    await page.route('**/api/v1/support/message*', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          error: {
            code: 'SUPPORT_SUBMIT_FAILED',
            message: 'Failed to submit support message',
          },
        }),
      });
    });

    await page.goto('/help');
    await page
      .getByPlaceholder('Tell us what you need help with...')
      .fill('The help form is broken');
    await page.getByRole('button', { name: /send to support/i }).click();

    await expect(page.getByRole('heading', { name: 'Support request failed' })).toBeVisible({
      timeout: 5000,
    });
  });
});
