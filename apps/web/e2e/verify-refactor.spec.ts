/**
 * Targeted e2e verification for the API client consolidation + auth refactor.
 */
import { test, expect } from '@playwright/test';

const AUTH_COOKIE = { name: 'goblin_auth', value: '1', domain: 'localhost', path: '/' };

const MODELS_MOCK = {
  providers: [{ id: 'openai' }],
  models: [
    { provider: 'openai', name: 'gpt-4o', is_selectable: true, health: 'healthy' },
    { provider: 'openai', name: 'gpt-4o-mini', is_selectable: true, health: 'healthy' },
    {
      provider: 'openai',
      name: 'old-model',
      is_selectable: false,
      health: 'unhealthy',
      health_reason: 'Deprecated',
    },
  ],
};

async function mockCommon(page: import('@playwright/test').Page) {
  await page.route('**/api/models**', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MODELS_MOCK) })
  );
  await page.route('**/api/system-status**', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ models: 'ok', routing: 'ok' }),
    })
  );
  await page.route('**/api/auth/validate', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        valid: true,
        user: { id: 'u1', email: 'user@test.com', role: 'user' },
        expires_in: 3600,
      }),
    })
  );
  await page.route('**/health**', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ overall: 'healthy', services: {} }),
    })
  );
  await page.route('**/routing/info**', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
  );
  await page.route('**/chat/conversations**', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
  );
  await page.route('**/costs/summary**', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_cost: 0,
        cost_by_provider: {},
        cost_by_model: {},
        requests_by_provider: {},
      }),
    })
  );
  await page.route('**/auth/csrf-token', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ csrf_token: 'csrf-e2e' }),
    })
  );
}

async function setAuthSession(
  page: import('@playwright/test').Page,
  context: import('@playwright/test').BrowserContext
) {
  await context.addCookies([AUTH_COOKIE]);
  await page.addInitScript(() => {
    window.localStorage.removeItem('auth_token');
    window.localStorage.setItem(
      'user_data',
      JSON.stringify({ id: 'u1', email: 'user@test.com', role: 'user' })
    );
  });
}

// ── Auth flow ────────────────────────────────────────────────────────────────

test('login page renders email/password/sign-in', async ({ page }) => {
  await mockCommon(page);
  await page.goto('/login');
  await expect(page.getByLabel(/email/i)).toBeVisible();
  await expect(page.getByLabel(/^password$/i)).toBeVisible();
  await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
});

test('middleware blocks unauthenticated /chat and redirects to /login', async ({ page }) => {
  await page.goto('/chat');
  await expect(page).toHaveURL(/\/login/);
});

test('HttpOnly cookie path — goblin_auth=1 allows /chat without localStorage token', async ({
  page,
  context,
}) => {
  await mockCommon(page);
  await setAuthSession(page, context);
  await page.goto('/chat', { waitUntil: 'networkidle' });
  await expect(page).not.toHaveURL(/\/login/);
});

test('login 401 — stays on /login and button recovers (interceptor fix)', async ({ page }) => {
  await mockCommon(page);
  // 401 on login should NOT trigger a token-refresh attempt any more
  await page.route('**/auth/login', (r) =>
    r.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Invalid credentials' }),
    })
  );

  await page.goto('/login');
  await page.getByLabel(/email/i).fill('bad@example.com');
  await page.getByLabel(/^password$/i).fill('wrongpassword');
  await page.getByRole('button', { name: /sign in/i }).click();

  // URL stays on login
  await expect(page).toHaveURL(/\/login/);
  // Button recovers to clickable state (the fix: no more hanging refresh attempt)
  await expect(page.getByRole('button', { name: /sign in/i })).toBeEnabled({ timeout: 10_000 });
});

// ── Model registry ───────────────────────────────────────────────────────────

test('/api/models Next.js route exists and returns JSON regardless of backend state', async ({
  page,
}) => {
  // Hit the real Next.js /api/models endpoint — it proxies to the backend.
  // Backend may be unreachable in local dev (502), but the route must always return JSON,
  // never crash with an unhandled 500 or HTML error page.
  const response = await page.request.get('/api/models');
  const contentType = response.headers()['content-type'] ?? '';
  expect(contentType).toContain('application/json');

  const body = await response.json();
  if (response.ok()) {
    // Backend reachable: expect model list in body or data.models
    const models = body?.data?.models ?? body?.models;
    expect(Array.isArray(models)).toBe(true);
  } else {
    // Backend unreachable (502/503): should return a structured error, not raw HTML
    expect(typeof body).toBe('object');
  }
});

test('/api/models is called during chat load (model registry path active)', async ({
  page,
  context,
}) => {
  let modelsCalled = false;

  // Set up common mocks first, then override model route with tracker
  await mockCommon(page);
  // Override AFTER mockCommon so this handler takes precedence
  await page.route('**/api/models**', async (r) => {
    modelsCalled = true;
    await r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MODELS_MOCK),
    });
  });

  await setAuthSession(page, context);
  await page.goto('/chat', { waitUntil: 'networkidle' });
  expect(modelsCalled).toBe(true);
});

// ── Dashboard / getCostSummary ───────────────────────────────────────────────

test('dashboard loads without JS errors when /costs/summary is empty', async ({
  page,
  context,
}) => {
  const jsErrors: string[] = [];
  page.on('pageerror', (e) => jsErrors.push(e.message));

  await mockCommon(page);
  await setAuthSession(page, context);
  await page.goto('/chat', { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);

  const realErrors = jsErrors.filter((e) => !e.includes('ResizeObserver') && !e.includes('hydrat'));
  expect(realErrors).toHaveLength(0);
});
