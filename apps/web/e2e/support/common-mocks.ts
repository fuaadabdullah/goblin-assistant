import type { Page } from '@playwright/test';

const MOCK_MODELS_RESPONSE = {
  providers: [
    {
      id: 'openai',
      name: 'OpenAI',
      enabled: true,
      configured: true,
      health: 'healthy',
      status: 'healthy',
      models: ['gpt-4o-mini'],
    },
  ],
  models: [
    {
      provider: 'openai',
      name: 'gpt-4o-mini',
      is_selectable: true,
      health: 'healthy',
      health_reason: null,
    },
  ],
  total_providers: 1,
  total_models: 1,
};

const mockSystemStatusResponse = () => ({
  models: 'ok',
  routing: 'ok',
  sandbox: 'ok',
  updatedAt: new Date().toISOString(),
});

export const mockCommonApiRoutes = async (page: Page): Promise<void> => {
  await page.route('**/api/models*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_MODELS_RESPONSE),
    });
  });

  await page.route('**/api/system-status*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockSystemStatusResponse()),
    });
  });
};
