import { expect, test } from '@playwright/test';
import { mockCommonApiRoutes } from './support/common-mocks';

const providerSettings = [
  {
    id: 1,
    name: 'openai',
    enabled: true,
    configured: true,
    models: ['gpt-4o-mini'],
  },
  {
    id: 2,
    name: 'anthropic',
    enabled: false,
    configured: false,
    models: ['claude-3-haiku'],
  },
];

test.describe('Onboarding flow', () => {
  test.beforeEach(async ({ page }) => {
    await mockCommonApiRoutes(page);

    await page.route('**/api/settings/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 300));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(providerSettings),
      });
    });
  });

  test('loads provider settings, walks the wizard, and marks onboarding complete', async ({
    page,
  }) => {
    await page.goto('/onboarding', { waitUntil: 'domcontentloaded' });

    await expect(page.getByText('Checking provider configuration...')).toBeVisible();
    await expect(page.getByText('1 provider ready for use.')).toBeVisible();
    await expect(page.getByText('Provider ready', { exact: true })).toBeVisible();
    await expect(page.getByText('2 providers found')).toBeVisible();

    await page.getByRole('button', { name: 'Next', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'First chat' })).toBeVisible();

    await page.getByRole('button', { name: /Compare provider options/i }).click();
    await expect(page.getByRole('link', { name: 'Start chat' })).toHaveAttribute(
      'href',
      expect.stringContaining('Compare%20provider%20options')
    );

    await page.getByRole('button', { name: 'Next', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Search demo' })).toBeVisible();

    await page.getByRole('button', { name: 'Complete' }).click();

    await expect.poll(async () => page.evaluate(() => localStorage.getItem('goblinos-onboarding-complete'))).toBe(
      'true'
    );
    await expect(page).toHaveURL(/\/$/);
  });
});
