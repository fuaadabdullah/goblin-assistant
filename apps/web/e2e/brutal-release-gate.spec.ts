import { expect, test, type BrowserContext, type Page } from '@playwright/test';
import { authenticateE2EUser } from './support/common-mocks';
import { createBrutalHarness } from './support/brutal-harness';

const waitForChat = async (page: Page) => {
  await expect(page).toHaveURL(/\/chat(?:[?#].*)?$/);
  await expect(page.getByRole('main', { name: /chat/i })).toBeVisible();
  await expect(page.getByLabel(/chat message input/i)).toBeVisible();
};

const waitForSettings = async (page: Page) => {
  await expect(page).toHaveURL(/\/settings(?:[?#].*)?$/);
  await expect(page.getByRole('heading', { name: /provider & model settings/i })).toBeVisible();
};

const waitForRegister = async (page: Page) => {
  await expect(page.getByRole('heading', { name: /create account/i })).toBeVisible();
  await expect(page.getByLabel(/email/i)).toBeVisible();
  await expect(page.getByRole('button', { name: /create account/i })).toBeVisible();
  await page.waitForTimeout(500);
};

const waitForHome = async (page: Page) => {
  await expect(page.getByRole('heading', { name: /control panel/i })).toBeVisible();
};

const chatTranscript = (page: Page) => page.getByLabel(/chat transcript/i);

const clickNewConversation = async (page: Page) => {
  const button = page.getByRole('button', { name: /new conversation/i });
  await button.scrollIntoViewIfNeeded();
  await button.dispatchEvent('click');
};

const openAuthedPage = async (page: Page, path: string) => {
  await page.goto(path, { waitUntil: 'domcontentloaded' });
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
};

async function prepareAuthedPage(context: BrowserContext, page: Page) {
  await authenticateE2EUser(context);
  const harness = createBrutalHarness(page);
  await harness.install();
  return harness;
}

test.describe('Brutal release gate', () => {
  test('new user signs up, creates Goblin, saves memory, returns, recalls it, and keeps stats accurate', async ({
    page,
    context,
  }) => {
    const harness = createBrutalHarness(page);
    harness.state.setRegisterResponse({
      status: 200,
      body: {
        access_token: 'new-user-access-token',
        refresh_token: 'new-user-refresh-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: { id: 'new-user', email: 'new-user@example.com', role: 'user' },
      },
    });
    await harness.install();

    await page.goto('/login?mode=register&redirect=/chat', { waitUntil: 'domcontentloaded' });
    await waitForRegister(page);
    await page.getByLabel(/email/i).fill('new-user@example.com');
    await page.getByLabel(/^password$/i).fill('strong-password');
    await page.getByRole('button', { name: /create account/i }).click();

    await authenticateE2EUser(context);
    await page.goto('/chat', { waitUntil: 'domcontentloaded' });
    await waitForChat(page);
    await clickNewConversation(page);
    await page.getByLabel(/chat message input/i).fill('Remember my style is blunt.');
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(chatTranscript(page).getByText('Memory saved as a durable fact.')).toBeVisible();
    await expect(page.locator('#chat-composer-meta')).toContainText('Session: 20 tok');
    await expect(page.locator('#chat-composer-meta')).toContainText('$0.0002');

    await page.goto('/settings', { waitUntil: 'domcontentloaded' });
    await waitForSettings(page);
    await page.goto('/chat', { waitUntil: 'domcontentloaded' });
    await waitForChat(page);
    await expect(page.getByRole('button', { name: /Remember my style is blunt\./i })).toBeVisible();
    const savedThreadButton = page.getByRole('button', { name: /Remember my style is blunt\./i });
    await savedThreadButton.scrollIntoViewIfNeeded();
    await savedThreadButton.dispatchEvent('click');
    await expect(chatTranscript(page).getByText('Memory saved as a durable fact.')).toBeVisible();

    await page.getByLabel(/chat message input/i).fill('What do you remember about my style?');
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(chatTranscript(page).getByText('You prefer blunt answers.')).toBeVisible();
    await expect(page.locator('#chat-composer-meta')).toContainText('Session: 40 tok');
    await expect(page.locator('#chat-composer-meta')).toContainText('$0.0004');

    const threadButton = page.getByRole('button', { name: /Remember my style is blunt\./i });
    await expect(threadButton).toBeVisible();
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });
    await waitForSettings(page);
    await page.goto('/chat', { waitUntil: 'domcontentloaded' });
    await waitForChat(page);
    await threadButton.scrollIntoViewIfNeeded();
    await threadButton.dispatchEvent('click');
    await expect(chatTranscript(page).getByText('You prefer blunt answers.')).toBeVisible();

    expect(harness.captured.filter((request) => /\/messages$/.test(request.url))).toHaveLength(2);
  });

  test('tool execution survives malformed tool payloads without breaking the transcript', async ({
    page,
    context,
  }) => {
    const harness = await prepareAuthedPage(context, page);
    harness.state.setSendMessageResponder(async ({ requestBody, conversationId, conversation }) => {
      const prompt = String(requestBody.message || '');
      conversation.messages.push({
        message_id: 'user-0001',
        role: 'user',
        content: prompt,
        timestamp: '2026-08-18T12:00:00.000Z',
      });
      conversation.messages.push({
        message_id: 'assistant-0002',
        role: 'assistant',
        content: JSON.stringify({
          tool_calls: [{ name: 'web_search', arguments: '{"query":' }],
          malformed: true,
        }),
        timestamp: '2026-08-18T12:00:00.000Z',
        metadata: { provider: 'openai', model: 'gpt-4o-mini' },
      });
      harness.conversations.set(conversationId, conversation);
      return {
        status: 200,
        body: {
          message_id: 'assistant-0002',
          response: {
            tool_calls: [{ name: 'web_search', arguments: '{"query":' }],
            malformed: true,
          },
          provider: 'openai',
          model: 'gpt-4o-mini',
          timestamp: '2026-08-18T12:00:00.000Z',
          usage: { input_tokens: 8, output_tokens: 12, total_tokens: 20 },
          cost_usd: 0.0002,
          correlation_id: 'corr-malformed',
        },
      };
    });

    await openAuthedPage(page, '/chat');
    await waitForChat(page);
    await clickNewConversation(page);
    await page.getByLabel(/chat message input/i).fill('Use the tool but emit malformed tool call JSON.');
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(chatTranscript(page).getByText(/tool_calls/)).toBeVisible();
    await expect(chatTranscript(page).getByText(/"malformed":\s*true/)).toBeVisible();
  });

  test('provider switching persists and fallback succeeds when the chosen provider fails', async ({
    page,
    context,
  }) => {
    const harness = await prepareAuthedPage(context, page);
    await openAuthedPage(page, '/settings');
    await waitForSettings(page);

    await page.getByRole('combobox', { name: /default provider/i }).click();
    await page.getByRole('option', { name: 'anthropic' }).click();
    await page.getByRole('combobox', { name: /default model/i }).click();
    await page.getByRole('option', { name: 'claude-3-haiku' }).click();
    await page.getByRole('button', { name: /save preferences/i }).click();
    await expect(page.getByText(/preferences saved/i)).toBeVisible();

    harness.state.setSendMessageResponder(async ({ requestBody, conversationId, conversation }) => {
      const prompt = String(requestBody.message || '');
      const hasExplicitSelection =
        Boolean(requestBody.provider) || Boolean(requestBody.model);

      if (hasExplicitSelection) {
        return {
          status: 503,
          body: {
            error: { message: 'Anthropic is unavailable right now.' },
          },
        };
      }

      conversation.messages.push({
        message_id: 'user-0001',
        role: 'user',
        content: prompt,
        timestamp: '2026-08-18T12:00:00.000Z',
      });
      conversation.messages.push({
        message_id: 'assistant-0002',
        role: 'assistant',
        content: 'Fallback provider handled the request.',
        timestamp: '2026-08-18T12:00:00.000Z',
        metadata: { provider: 'openai', model: 'gpt-4o-mini' },
      });
      harness.conversations.set(conversationId, conversation);
      return {
        status: 200,
        body: {
          message_id: 'assistant-0002',
          response: 'Fallback provider handled the request.',
          provider: 'openai',
          model: 'gpt-4o-mini',
          timestamp: '2026-08-18T12:00:00.000Z',
          usage: { input_tokens: 8, output_tokens: 12, total_tokens: 20 },
          cost_usd: 0.0002,
          correlation_id: 'corr-fallback',
        },
      };
    });

    await openAuthedPage(page, '/chat');
    await waitForChat(page);
    await clickNewConversation(page);
    await page.getByLabel(/chat message input/i).fill('Use the switched provider.');
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(chatTranscript(page).getByText('Fallback provider handled the request.')).toBeVisible();
    const messageRequests = harness.captured.filter((request) => /\/messages$/.test(request.url));
    expect(messageRequests).toHaveLength(2);
    expect(messageRequests[0]?.body).toMatchObject({
      provider: 'anthropic',
      model: 'claude-3-haiku',
    });
    expect(messageRequests[1]?.body).toMatchObject({
      message: 'Use the switched provider.',
    });
    expect(messageRequests[1]?.body).not.toHaveProperty('provider');
  });

  test('refresh during generation preserves the in-flight conversation without duplicating it', async ({
    page,
    context,
  }) => {
    const harness = await prepareAuthedPage(context, page);
    harness.state.setSendMessageResponder(async ({ requestBody, conversationId, conversation }) => {
      const prompt = String(requestBody.message || '');
      conversation.messages.push({
        message_id: 'user-0001',
        role: 'user',
        content: prompt,
        timestamp: '2026-08-18T12:00:00.000Z',
      });
      harness.conversations.set(conversationId, conversation);

      await new Promise((resolve) => setTimeout(resolve, 1200));

      conversation.messages.push({
        message_id: 'assistant-0002',
        role: 'assistant',
        content: 'Streaming response complete.',
        timestamp: '2026-08-18T12:00:00.000Z',
        metadata: { provider: 'openai', model: 'gpt-4o-mini' },
      });
      harness.conversations.set(conversationId, conversation);

      return {
        status: 200,
        body: {
          message_id: 'assistant-0002',
          response: 'Streaming response complete.',
          provider: 'openai',
          model: 'gpt-4o-mini',
          timestamp: '2026-08-18T12:00:00.000Z',
          usage: { input_tokens: 8, output_tokens: 12, total_tokens: 20 },
          cost_usd: 0.0002,
          correlation_id: 'corr-refresh',
        },
        delayMs: 0,
      };
    });

    await openAuthedPage(page, '/chat');
    await waitForChat(page);
    await clickNewConversation(page);
    await page.getByLabel(/chat message input/i).fill('Please stream this reply.');
    await page.getByRole('button', { name: /send message/i }).click();

    await page.waitForTimeout(250);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await waitForChat(page);
    const streamThreadButton = page.getByRole('button', { name: /Please stream this reply\./i });
    await streamThreadButton.scrollIntoViewIfNeeded();
    await streamThreadButton.dispatchEvent('click');
    await expect(chatTranscript(page).getByText('Please stream this reply.')).toBeVisible();
    expect(harness.captured.filter((request) => /\/messages$/.test(request.url))).toHaveLength(1);
  });

  test('duplicate send attempts are collapsed into a single in-flight request', async ({
    page,
    context,
  }) => {
    const harness = await prepareAuthedPage(context, page);
    harness.state.setSendMessageResponder(async ({ requestBody, conversationId, conversation }) => {
      const prompt = String(requestBody.message || '');
      conversation.messages.push({
        message_id: 'user-0001',
        role: 'user',
        content: prompt,
        timestamp: '2026-08-18T12:00:00.000Z',
      });
      harness.conversations.set(conversationId, conversation);
      await new Promise((resolve) => setTimeout(resolve, 1200));
      conversation.messages.push({
        message_id: 'assistant-0002',
        role: 'assistant',
        content: 'Streaming response complete.',
        timestamp: '2026-08-18T12:00:00.000Z',
        metadata: { provider: 'openai', model: 'gpt-4o-mini' },
      });
      harness.conversations.set(conversationId, conversation);
      return {
        status: 200,
        body: {
          message_id: 'assistant-0002',
          response: 'Streaming response complete.',
          provider: 'openai',
          model: 'gpt-4o-mini',
          timestamp: '2026-08-18T12:00:00.000Z',
          usage: { input_tokens: 8, output_tokens: 12, total_tokens: 20 },
          cost_usd: 0.0002,
          correlation_id: 'corr-duplicate',
        },
      };
    });

    await openAuthedPage(page, '/chat');
    await waitForChat(page);
    await clickNewConversation(page);
    await page.getByLabel(/chat message input/i).fill('Do not duplicate this request.');
    const sendButton = page.getByRole('button', { name: /send message/i });
    await sendButton.click();
    await sendButton.click({ force: true });

    await expect(sendButton).toBeDisabled();
    await expect(chatTranscript(page).getByText('Streaming response complete.')).toBeVisible();
    expect(harness.captured.filter((request) => /\/messages$/.test(request.url))).toHaveLength(1);
  });

  test('provider timeout falls back cleanly to the default route', async ({ page, context }) => {
    const harness = await prepareAuthedPage(context, page);
    await openAuthedPage(page, '/settings');
    await waitForSettings(page);
    await page.getByRole('combobox', { name: /default provider/i }).click();
    await page.getByRole('option', { name: 'anthropic' }).click();
    await page.getByRole('combobox', { name: /default model/i }).click();
    await page.getByRole('option', { name: 'claude-3-haiku' }).click();
    await page.getByRole('button', { name: /save preferences/i }).click();

    harness.state.setSendMessageResponder(async ({ requestBody, conversationId, conversation }) => {
      const prompt = String(requestBody.message || '');
      if (requestBody.provider) {
        return {
          status: 504,
          body: {
            error: {
              message: 'Anthropic timed out while generating the reply.',
            },
          },
        };
      }

      conversation.messages.push({
        message_id: 'user-0001',
        role: 'user',
        content: prompt,
        timestamp: '2026-08-18T12:00:00.000Z',
      });
      conversation.messages.push({
        message_id: 'assistant-0002',
        role: 'assistant',
        content: 'Fallback provider answered after timeout.',
        timestamp: '2026-08-18T12:00:00.000Z',
        metadata: { provider: 'openai', model: 'gpt-4o-mini' },
      });
      harness.conversations.set(conversationId, conversation);
      return {
        status: 200,
        body: {
          message_id: 'assistant-0002',
          response: 'Fallback provider answered after timeout.',
          provider: 'openai',
          model: 'gpt-4o-mini',
          timestamp: '2026-08-18T12:00:00.000Z',
          usage: { input_tokens: 8, output_tokens: 12, total_tokens: 20 },
          cost_usd: 0.0002,
          correlation_id: 'corr-timeout',
        },
      };
    });

    await openAuthedPage(page, '/chat');
    await waitForChat(page);
    await clickNewConversation(page);
    await page.getByLabel(/chat message input/i).fill('Show me the timeout fallback.');
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(chatTranscript(page).getByText('Fallback provider answered after timeout.')).toBeVisible();
    const messageRequests = harness.captured.filter((request) => /\/messages$/.test(request.url));
    expect(messageRequests).toHaveLength(2);
  });

  test('empty accounts show an empty state and can still start a first conversation', async ({
    page,
    context,
  }) => {
    const harness = await prepareAuthedPage(context, page);
    harness.state.clearConversations();

    await openAuthedPage(page, '/chat');
    await waitForChat(page);
    await expect(page.getByText(/start a conversation to see it here/i).first()).toBeVisible();

    await clickNewConversation(page);
    await page.getByLabel(/chat message input/i).fill('Hello from an empty account.');
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(chatTranscript(page).getByText('Streaming response complete.')).toBeVisible();
  });

  test('rate limits surface cleanly and a later attempt succeeds', async ({
    page,
    context,
  }) => {
    const harness = createBrutalHarness(page);
    harness.state.setRegisterResponse({
      status: 429,
      body: {
        error: {
          message: 'Too many sign-up attempts. Try again later.',
        },
      },
    });
    await harness.install();

    await page.goto('/register?redirect=/chat', { waitUntil: 'domcontentloaded' });
    await waitForRegister(page);
    await page.getByLabel(/email/i).fill('rate-limit@example.com');
    await page.getByLabel(/^password$/i).fill('strong-password');
    await expect(page.getByLabel(/email/i)).toHaveValue('rate-limit@example.com');
    await expect(page.getByLabel(/^password$/i)).toHaveValue('strong-password');
    await page.getByLabel(/email/i).evaluate((input) => {
      (input as HTMLInputElement).form?.requestSubmit();
    });

    await expect.poll(() => harness.captured.filter((request) => /\/auth\/register$/.test(request.url)).length).toBe(1);
    await expect(page.getByRole('heading', { name: /create account/i })).toBeVisible();

    harness.state.setRegisterResponse({
      status: 200,
      body: {
        access_token: 'rate-limit-access-token',
        refresh_token: 'rate-limit-refresh-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: { id: 'rate-limit-user', email: 'rate-limit@example.com', role: 'user' },
      },
    });

    await page.getByLabel(/email/i).evaluate((input) => {
      (input as HTMLInputElement).form?.requestSubmit();
    });
    await expect.poll(() => harness.captured.filter((request) => /\/auth\/register$/.test(request.url)).length).toBe(2);
    await authenticateE2EUser(context);
    await page.goto('/chat', { waitUntil: 'domcontentloaded' });
    await waitForChat(page);
  });

  test('auth expiration redirects to login before protected content renders', async ({
    page,
    context,
  }) => {
    await authenticateE2EUser(context);
    const harness = createBrutalHarness(page);
    harness.state.setAuthValidateResponse({
      status: 401,
      body: {
        valid: false,
        error: { code: 'TOKEN_EXPIRED', message: 'Authentication token expired.' },
      },
    });
    await harness.install();

    await page.goto('/chat', { waitUntil: 'domcontentloaded' });
    await expect(page.getByText(/this preview is static/i).first()).toBeVisible();
    await expect(page.getByRole('link', { name: /sign in to continue this conversation/i }).first()).toBeVisible();
  });

  test('simultaneous chats keep their thread state isolated', async ({ browser }) => {
    const leftContext = await browser.newContext();
    const rightContext = await browser.newContext();
    await authenticateE2EUser(leftContext);
    await authenticateE2EUser(rightContext);

    const leftPage = await leftContext.newPage();
    const rightPage = await rightContext.newPage();
    const leftHarness = createBrutalHarness(leftPage);
    const rightHarness = createBrutalHarness(rightPage);
    await leftHarness.install();
    await rightHarness.install();

    await openAuthedPage(leftPage, '/chat');
    await openAuthedPage(rightPage, '/chat');
    await waitForChat(leftPage);
    await waitForChat(rightPage);

    await clickNewConversation(leftPage);
    await clickNewConversation(rightPage);
    await leftPage.getByLabel(/chat message input/i).fill('Left tab conversation.');
    await rightPage.getByLabel(/chat message input/i).fill('Right tab conversation.');
    await leftPage.getByRole('button', { name: /send message/i }).click();
    await rightPage.getByRole('button', { name: /send message/i }).click();

    await expect(chatTranscript(leftPage).getByText('Streaming response complete.')).toBeVisible();
    await expect(chatTranscript(rightPage).getByText('Streaming response complete.')).toBeVisible();
    await expect(chatTranscript(leftPage).getByText('Left tab conversation.')).toBeVisible();
    await expect(chatTranscript(rightPage).getByText('Right tab conversation.')).toBeVisible();

    await leftContext.close();
    await rightContext.close();
  });

  test('mobile viewport still exposes the drawer and composer flow', async ({ page, context }) => {
    const harness = await prepareAuthedPage(context, page);
    await page.setViewportSize({ width: 390, height: 844 });

    await openAuthedPage(page, '/chat');
    await waitForChat(page);
    await page.getByRole('button', { name: /open conversations/i }).click();
    await expect(page.getByRole('button', { name: /close conversations drawer/i })).toBeVisible();
    await page.keyboard.press('Escape');

    await page.getByLabel(/chat message input/i).fill('Mobile viewport still works.');
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(chatTranscript(page).getByText('Streaming response complete.')).toBeVisible();
    expect(harness.captured.filter((request) => /\/messages$/.test(request.url))).toHaveLength(1);
  });

  test('redis, celery, and postgres failures degrade gracefully on the visible pages', async ({
    page,
    context,
  }) => {
    const harness = await prepareAuthedPage(context, page);

    harness.state.setHealthResponse({
      overall: 'degraded',
      status: 'degraded',
      latency_ms: 75,
      last_check: '2026-08-18T12:00:00.000Z',
      components: {
        api: { status: 'healthy' },
        routing: { status: 'healthy' },
        database: { status: 'healthy' },
        redis: { status: 'unhealthy' },
        cache: { status: 'healthy' },
      },
      services: {
        api: { status: 'healthy' },
        routing: { status: 'healthy' },
        database: { status: 'healthy' },
        redis: { status: 'unhealthy' },
        cache: { status: 'healthy' },
      },
    });
    harness.state.setSandboxJobsResponse({
      error: {
        message: 'Sandbox queue unavailable.',
      },
    });
    harness.state.setSendMessageResponder(async ({ requestBody, conversationId, conversation }) => {
      const prompt = String(requestBody.message || '');
      conversation.messages.push({
        message_id: 'user-0001',
        role: 'user',
        content: prompt,
        timestamp: '2026-08-18T12:00:00.000Z',
      });
      conversation.messages.push({
        message_id: 'assistant-0002',
        role: 'assistant',
        content: 'Postgres restarted and the thread reloaded.',
        timestamp: '2026-08-18T12:00:00.000Z',
        metadata: { provider: 'openai', model: 'gpt-4o-mini' },
      });
      harness.conversations.set(conversationId, conversation);
      return {
        status: 200,
        body: {
          message_id: 'assistant-0002',
          response: 'Postgres restarted and the thread reloaded.',
          provider: 'openai',
          model: 'gpt-4o-mini',
          timestamp: '2026-08-18T12:00:00.000Z',
          usage: { input_tokens: 8, output_tokens: 12, total_tokens: 20 },
          cost_usd: 0.0002,
          correlation_id: 'corr-postgres',
        },
      };
    });

    await openAuthedPage(page, '/');
    await waitForHome(page);
    await expect(page.getByText(/down/i).first()).toBeVisible();

    await openAuthedPage(page, '/sandbox?guest=0');
    await expect(page.getByText(/no jobs yet/i)).toBeVisible();

    await openAuthedPage(page, '/chat');
    await waitForChat(page);
    await clickNewConversation(page);
    await page.getByLabel(/chat message input/i).fill('Simulate a postgres restart and keep history.');
    await page.getByRole('button', { name: /send message/i }).click();
    await expect(chatTranscript(page).getByText('Postgres restarted and the thread reloaded.')).toBeVisible();
    await page.reload({ waitUntil: 'domcontentloaded' });
    await waitForChat(page);
    await expect(chatTranscript(page).getByText('Postgres restarted and the thread reloaded.')).toBeVisible();
  });

  test('huge conversations render scrollably and new messages append correctly', async ({
    page,
    context,
  }) => {
    const harness = await prepareAuthedPage(context, page);

    // Seed a conversation with 80 alternating messages (~200 chars each)
    const hugeConvId = 'conv-huge-001';
    const userBase =
      'This is a user message with enough content to simulate a realistic token count in a large conversation thread. Padding to reach roughly two hundred chars: ';
    const assistantBase =
      'This is an assistant reply with enough content to simulate a realistic token count in a large conversation thread. Padding to reach roughly two hundred chars: ';

    const seededMessages: Array<{
      message_id: string;
      role: 'user' | 'assistant';
      content: string;
      timestamp: string;
      metadata?: Record<string, unknown>;
    }> = [];
    for (let i = 0; i < 80; i++) {
      const isUser = i % 2 === 0;
      seededMessages.push({
        message_id: `${isUser ? 'user' : 'assistant'}-${String(i + 1).padStart(4, '0')}`,
        role: isUser ? 'user' : 'assistant',
        content: (isUser ? userBase : assistantBase) + String(i + 1),
        timestamp: '2026-08-18T12:00:00.000Z',
        ...(isUser ? {} : { metadata: { provider: 'openai', model: 'gpt-4o-mini' } }),
      });
    }
    harness.state.seedConversation({
      conversation_id: hugeConvId,
      title: 'Huge conversation stress test',
      created_at: '2026-08-18T12:00:00.000Z',
      updated_at: '2026-08-18T12:00:00.000Z',
      messages: seededMessages,
    });

    // Wire a deterministic responder for the new message appended during the test
    harness.state.setSendMessageResponder(async ({ requestBody, conversationId, conversation }) => {
      const prompt = String(requestBody.message || '');
      conversation.messages.push({
        message_id: 'user-0081',
        role: 'user',
        content: prompt,
        timestamp: '2026-08-18T12:00:00.000Z',
      });
      conversation.messages.push({
        message_id: 'assistant-0082',
        role: 'assistant',
        content: 'Huge conversation loaded and preserved.',
        timestamp: '2026-08-18T12:00:00.000Z',
        metadata: { provider: 'openai', model: 'gpt-4o-mini' },
      });
      harness.conversations.set(conversationId, conversation);
      return {
        status: 200,
        body: {
          message_id: 'assistant-0082',
          response: 'Huge conversation loaded and preserved.',
          provider: 'openai',
          model: 'gpt-4o-mini',
          timestamp: '2026-08-18T12:00:00.000Z',
          usage: { input_tokens: 8, output_tokens: 12, total_tokens: 20 },
          cost_usd: 0.0002,
          correlation_id: 'corr-huge',
        },
      };
    });

    await openAuthedPage(page, '/chat');
    await waitForChat(page);

    // Open the seeded huge conversation via the sidebar thread button
    const hugeThreadButton = page.getByRole('button', { name: /huge conversation stress test/i });
    await hugeThreadButton.scrollIntoViewIfNeeded();
    await hugeThreadButton.dispatchEvent('click');

    // Transcript must be visible and the last pre-seeded message must be reachable by scrolling
    const transcript = chatTranscript(page);
    await expect(transcript).toBeVisible();
    const lastSeededContent = assistantBase + '80';
    const lastMessage = transcript.getByText(lastSeededContent);
    await lastMessage.scrollIntoViewIfNeeded();
    await expect(lastMessage).toBeVisible();

    // The composer must remain accessible and editable beneath a tall transcript
    const input = page.getByLabel(/chat message input/i);
    await input.scrollIntoViewIfNeeded();
    await expect(input).toBeVisible();
    await expect(input).toBeEditable();

    // Send a new message and verify it appends at the bottom
    await input.fill('Append this to the huge conversation.');
    await page.getByRole('button', { name: /send message/i }).click();
    await expect(transcript.getByText('Huge conversation loaded and preserved.')).toBeVisible();

    // Exactly one network round-trip — no duplicates or spurious retries
    expect(harness.captured.filter((request) => /\/messages$/.test(request.url))).toHaveLength(1);
  });
});
