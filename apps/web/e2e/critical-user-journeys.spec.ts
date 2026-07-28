import { expect, type Page, test } from '@playwright/test';
import { authenticateE2EUser, mockCommonApiRoutes } from './support/common-mocks';

const nowIso = '2026-07-18T12:00:00.000Z';

type CapturedRequest = {
  url: string;
  method: string;
  body: Record<string, unknown>;
};

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
    enabled: true,
    configured: true,
    models: ['claude-3-haiku'],
  },
];

const historyThread = {
  conversation_id: 'conv-history',
  title: 'Saved memory plan',
  snippet: 'We decided to store durable facts.',
  created_at: nowIso,
  updated_at: nowIso,
  message_count: 2,
  category: 'research',
};

const historyConversation = {
  conversation_id: 'conv-history',
  title: 'Saved memory plan',
  created_at: nowIso,
  updated_at: nowIso,
  messages: [
    {
      message_id: 'msg-history-user',
      role: 'user',
      content: 'What did we decide about memory?',
      timestamp: nowIso,
      metadata: {},
    },
    {
      message_id: 'msg-history-assistant',
      role: 'assistant',
      content: 'We decided to store durable facts instead of raw transcripts.',
      timestamp: nowIso,
      metadata: { provider: 'openai', model: 'gpt-4o-mini' },
    },
  ],
  pagination: { offset: 0, limit: 50, total: 2, returned: 2, has_more: false },
};

async function mockCriticalJourneyApi(page: Page) {
  const captured: CapturedRequest[] = [];

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

  await page.route(/\/api\/settings\/?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(providerSettings),
    });
  });

  await page.route('**/api/account/preferences', async (route) => {
    const body = route.request().method() === 'PUT' ? route.request().postDataJSON() : {};
    captured.push({
      url: route.request().url(),
      method: route.request().method(),
      body,
    });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true }),
    });
  });

  await page.route('**/api/chat/estimate-tokens**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        input_tokens: 8,
        estimated_output_tokens: 32,
        estimated_cost_usd: 0.0004,
        provider: 'openai',
        model: 'gpt-4o-mini',
        layers: [{ name: 'message', tokens: 8 }],
        degraded_mode: false,
      }),
    });
  });

  await page.route('**/api/chat/upload-file', async (route) => {
    captured.push({
      url: route.request().url(),
      method: route.request().method(),
      body: { formData: true },
    });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        file_id: 'file-tool-context',
        filename: 'tool-context.txt',
        mime_type: 'text/plain',
        size_bytes: 22,
      }),
    });
  });

  await page.route(/\/api\/chat\/conversations\/conv-history(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(historyConversation),
    });
  });

  await page.route(/\/api\/chat\/conversations\/[^/]+\/messages$/, async (route) => {
    const body = route.request().postDataJSON();
    captured.push({
      url: route.request().url(),
      method: route.request().method(),
      body,
    });

    const message = String(body.message ?? '');
    const response = message.match(/remember/i)
      ? 'Memory saved as a durable fact.'
      : message.match(/web search|tool/i)
        ? 'Tool executed: web_search returned current context.'
        : 'Streaming response complete.';

    await new Promise((resolve) => setTimeout(resolve, message.match(/stream/i) ? 700 : 0));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        message_id: `msg-${captured.length}`,
        response,
        provider: body.provider || 'openai',
        model: body.model || 'gpt-4o-mini',
        timestamp: nowIso,
        usage: { input_tokens: 8, output_tokens: 12, total_tokens: 20 },
        cost_usd: 0.0002,
        correlation_id: `corr-${captured.length}`,
      }),
    });
  });

  await page.route(/\/api\/chat\/conversations(?:\?.*)?$/, async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([historyThread]),
      });
      return;
    }

    const body = route.request().postDataJSON();
    captured.push({
      url: route.request().url(),
      method: route.request().method(),
      body,
    });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        conversation_id: 'conv-new-critical',
        title: body.title || 'New critical journey chat',
        created_at: nowIso,
      }),
    });
  });

  await page.route('**/api/sandbox/jobs', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ jobs: [] }),
    });
  });

  await page.route('**/api/sandbox/run', async (route) => {
    const body = route.request().postDataJSON();
    captured.push({
      url: route.request().url(),
      method: route.request().method(),
      body,
    });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        output: 'sandbox-result: 42',
        job_id: 'job-critical',
      }),
    });
  });

  return {
    captured,
    findRequest: (pattern: RegExp) => captured.find((request) => pattern.test(request.url)),
  };
}

async function openAuthenticatedPage(page: Page, path: string) {
  await page.goto(path, { waitUntil: 'domcontentloaded' });
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });

  if (path.startsWith('/chat')) {
    await expect(page.getByRole('main', { name: /chat/i })).toBeVisible({ timeout: 15_000 });
    return;
  }

  if (path.startsWith('/settings')) {
    await expect(page.getByRole('heading', { name: /provider & model settings/i })).toBeVisible({
      timeout: 15_000,
    });
    return;
  }

  if (path.startsWith('/sandbox')) {
    await expect(page.getByRole('heading', { name: /safe experiments/i })).toBeVisible({
      timeout: 15_000,
    });
    return;
  }

  await expect(page.locator('body')).toBeVisible({ timeout: 15_000 });
}

function chatTranscript(page: Page) {
  return page.getByLabel(/chat transcript/i);
}

test.describe('Critical user journeys', () => {
  let api: Awaited<ReturnType<typeof mockCriticalJourneyApi>>;

  test('Journey 1: authentication gates protected pages and admits an authenticated session', async ({
    browser,
  }) => {
    const anonymousContext = await browser.newContext();
    const anonymousPage = await anonymousContext.newPage();
    await anonymousPage.goto('/chat');
    await expect(anonymousPage).toHaveURL(/\/login/);
    await expect(anonymousPage.getByLabel(/email/i)).toBeVisible();
    await expect(anonymousPage.getByLabel(/^password$/i)).toBeVisible();
    await anonymousContext.close();

    const authedContext = await browser.newContext();
    await authenticateE2EUser(authedContext);
    const authedPage = await authedContext.newPage();
    await mockCriticalJourneyApi(authedPage);
    await openAuthenticatedPage(authedPage, '/chat');
    await expect(authedPage).toHaveURL(/\/chat/);
    await expect(authedPage.getByLabel(/chat message input/i)).toBeVisible();
    await authedContext.close();
  });

  test.beforeEach(async ({ context, page }) => {
    await authenticateE2EUser(context);
    api = await mockCriticalJourneyApi(page);
  });

  test('Journey 2: new chat creates a backend conversation and sends the first message', async ({
    page,
  }) => {
    await openAuthenticatedPage(page, '/chat');
    await page.getByRole('button', { name: /new conversation/i }).click();
    await page.getByLabel(/chat message input/i).fill('Start a fresh planning chat.');
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(chatTranscript(page).getByText('Streaming response complete.')).toBeVisible();
    expect(api.findRequest(/\/api\/chat\/conversations$/)?.method).toBe('POST');
    expect(
      api.findRequest(/\/api\/chat\/conversations\/conv-new-critical\/messages$/)?.body
    ).toMatchObject({
      message: 'Start a fresh planning chat.',
    });
  });

  test('Journey 3: streaming response shows in-progress state before the assistant completes', async ({
    page,
  }) => {
    await openAuthenticatedPage(page, '/chat');
    await page.getByRole('button', { name: /new conversation/i }).click();
    await page.getByLabel(/chat message input/i).fill('Please stream a short response.');
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(page.getByRole('button', { name: /send message/i })).toBeDisabled();
    await expect(chatTranscript(page).getByText('Streaming response complete.')).toBeVisible();
  });

  test('Journey 4: tool execution request reaches the chat message endpoint', async ({ page }) => {
    await openAuthenticatedPage(page, '/chat');
    await page.getByRole('button', { name: /new conversation/i }).click();
    await page
      .getByLabel(/chat message input/i)
      .fill('Use the web search tool for current AI policy news.');
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(chatTranscript(page).getByText(/Tool executed: web_search/)).toBeVisible();
    expect(api.findRequest(/\/messages$/)?.body).toMatchObject({
      message: 'Use the web search tool for current AI policy news.',
    });
  });

  test('Journey 5: memory creation prompt is submitted and confirms durable memory', async ({
    page,
  }) => {
    await openAuthenticatedPage(page, '/chat');
    await page.getByRole('button', { name: /new conversation/i }).click();
    await page
      .getByLabel(/chat message input/i)
      .fill('Remember that my preferred deploy order is backend first.');
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(chatTranscript(page).getByText('Memory saved as a durable fact.')).toBeVisible();
    expect(api.findRequest(/\/messages$/)?.body).toMatchObject({
      message: 'Remember that my preferred deploy order is backend first.',
    });
  });

  test('Journey 6: conversation history loads an existing conversation transcript', async ({
    page,
  }) => {
    await openAuthenticatedPage(page, '/chat');
    await expect(page.getByRole('button', { name: /Saved memory plan/i })).toBeVisible();
    await page.getByRole('button', { name: /Saved memory plan/i }).click();
    await expect(
      page.getByText('We decided to store durable facts instead of raw transcripts.')
    ).toBeVisible();
  });

  test('Journey 7: provider switching persists into the next chat request', async ({ page }) => {
    await openAuthenticatedPage(page, '/settings');

    await page.getByRole('combobox', { name: /default provider/i }).click();
    await page.getByRole('option', { name: 'anthropic' }).click();
    await page.getByRole('combobox', { name: /default model/i }).click();
    await page.getByRole('option', { name: 'claude-3-haiku' }).click();
    await page.getByRole('button', { name: /save preferences/i }).click();

    await openAuthenticatedPage(page, '/chat');
    await page.getByRole('button', { name: /new conversation/i }).click();
    await page.getByLabel(/chat message input/i).fill('Send this with the switched provider.');
    await page.getByRole('button', { name: /send message/i }).click();
    await expect(chatTranscript(page).getByText('Streaming response complete.')).toBeVisible();

    expect(api.findRequest(/\/messages$/)?.body).toMatchObject({
      message: 'Send this with the switched provider.',
      provider: 'anthropic',
      model: 'claude-3-haiku',
    });
  });

  test('Journey 8: sandbox execution posts code and renders output logs', async ({ page }) => {
    await openAuthenticatedPage(page, '/sandbox');
    await page.getByPlaceholder(/enter your python code here/i).fill('print(40 + 2)');
    await page.getByRole('button', { name: /run code/i }).click();

    await expect(page.getByText('sandbox-result: 42')).toBeVisible();
    expect(api.findRequest(/\/api\/sandbox\/run$/)?.body).toMatchObject({
      source: 'print(40 + 2)',
      language: 'python',
    });
  });

  test('Journey 9: settings saves model preferences without leaving the page', async ({ page }) => {
    await openAuthenticatedPage(page, '/settings');
    await page.getByRole('button', { name: /save preferences/i }).click();

    await expect(page).toHaveURL(/\/settings/);
    expect(api.findRequest(/\/api\/account\/preferences$/)?.body).toMatchObject({
      default_provider: 'openai',
    });
  });
});
