import type { BrowserContext, Page } from '@playwright/test';

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
    {
      id: 'anthropic',
      name: 'Anthropic',
      enabled: true,
      configured: true,
      health: 'healthy',
      status: 'healthy',
      models: ['claude-3-haiku'],
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
    {
      provider: 'anthropic',
      name: 'claude-3-haiku',
      is_selectable: true,
      health: 'healthy',
      health_reason: null,
    },
  ],
  total_providers: 2,
  total_models: 2,
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

export const E2E_USER = {
  id: 'test_user',
  email: 'test@example.com',
  role: 'authenticated',
  created_at: '2026-01-01T00:00:00.000Z',
  user_metadata: { name: 'E2E User' },
};

export const authenticateE2EUser = async (context: BrowserContext): Promise<void> => {
  await context.addCookies([
    { name: 'goblin_auth', value: '1', domain: 'localhost', path: '/' },
    { name: 'goblin_e2e_auth', value: '1', domain: 'localhost', path: '/' },
    { name: 'session_token', value: 'mock-session-token-e2e', domain: 'localhost', path: '/' },
  ]);

  await context.addInitScript(
    ({ user }) => {
      const session = {
        access_token: 'mock-access-token-e2e',
        refresh_token: 'mock-refresh-token-e2e',
        token_type: 'bearer',
        expires_in: 3600,
        expires_at: Math.floor(Date.now() / 1000) + 3600,
        user,
      };
      const sessionJson = JSON.stringify(session);
      const sessionKeys = ['sb-placeholder-auth-token'];

      for (const key of sessionKeys) {
        window.localStorage.setItem(key, sessionJson);
      }
      window.localStorage.setItem(
        'user_data',
        JSON.stringify({ id: user.id, email: user.email, role: 'user', name: 'E2E User' })
      );
      window.localStorage.setItem('auth_token', session.access_token);
      window.localStorage.setItem('goblin_e2e_auth', '1');

      const originalGetItem = Storage.prototype.getItem;
      Storage.prototype.getItem = function patchedGetItem(key: string) {
        if (key.startsWith('sb-') && key.endsWith('-auth-token')) {
          return originalGetItem.call(this, key) ?? sessionJson;
        }
        return originalGetItem.call(this, key);
      };
    },
    { user: E2E_USER }
  );
};
