import { expect, test } from '@playwright/test';
import { authenticateE2EUser, mockCommonApiRoutes } from './support/common-mocks';

test.describe('Help: Support submission', () => {
  test.beforeEach(async ({ page, context }) => {
    await mockCommonApiRoutes(page);
    await authenticateE2EUser(context);

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

  });

  test('submits a support message and shows confirmation', async ({ page }) => {
    let submittedMessage = '';

    await page.route('**/api/support/message*', async (route) => {
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
    await page.route('**/api/support/message*', async (route) => {
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
