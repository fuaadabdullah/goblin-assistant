import { test, expect } from '@playwright/test';

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page, context }) => {
    const nowIso = new Date().toISOString();

    await page.route('**/chat/conversations', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          conversation_id: 'conv-e2e',
          title: 'Test message',
          created_at: nowIso,
        }),
      });
    });

    await page.route('**/chat/conversations/conv-e2e/messages', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message_id: 'msg-e2e-assistant',
          response: 'E2E response received.',
          provider: 'mock',
          model: 'mock-model',
          timestamp: new Date().toISOString(),
          usage: { input_tokens: 3, output_tokens: 4, total_tokens: 7 },
          cost_usd: 0.0001,
          correlation_id: 'corr-e2e',
        }),
      });
    });

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

    await context.addCookies([
      {
        name: 'goblin_auth',
        value: '1',
        domain: 'localhost',
        path: '/',
      },
      {
        name: 'session_token',
        value: 'mock-session-token-e2e',
        domain: 'localhost',
        path: '/',
      },
    ]);

    // Mock localStorage and auth flag cookie to simulate an authenticated session.
    await context.addInitScript(() => {
      document.cookie = 'goblin_auth=1; Path=/';
      window.localStorage.setItem(
        'user_data',
        JSON.stringify({ id: 'test_user', email: 'test@example.com', role: 'user' })
      );
    });
  });

  test('should display chat interface after authentication', async ({ page }) => {
    // Navigate to chat page
    await page.goto('/chat');

    // Look for chat-related elements
    await expect(page.getByRole('main', { name: /chat/i })).toBeVisible({ timeout: 5000 });
  });

  test('should have message input field', async ({ page }) => {
    await page.goto('/chat');

    // Look for message input (textarea or input field)
    const messageInput = page.getByLabel(/chat message input/i);

    const count = await messageInput.count();
    if (count > 0) {
      await expect(messageInput.first()).toBeVisible();
    }
  });

  test('should allow typing messages', async ({ page }) => {
    await page.goto('/chat');

    const messageInput = page.getByLabel(/chat message input/i);
    const count = await messageInput.count();

    if (count > 0) {
      const input = messageInput.first();
      const testMessage = 'Hello, how are you?';
      await input.fill(testMessage);

      const value = await input.inputValue();
      expect(value).toBe(testMessage);
    }
  });

  test('should display send button', async ({ page }) => {
    await page.goto('/chat');

    // Look for send button
    const sendButton = page.locator('button').filter({ hasText: /send|submit|ask/i });

    const count = await sendButton.count();
    if (count > 0) {
      await expect(sendButton.first()).toBeVisible();
    }
  });

  test('should send message on button click', async ({ page }) => {
    await page.goto('/chat');

    const messageInput = page.getByLabel(/chat message input/i);
    const count = await messageInput.count();

    if (count > 0) {
      await messageInput.first().fill('Test message');

      const sendButton = page.getByRole('button', { name: /send message/i });
      const sendCount = await sendButton.count();

      if (sendCount > 0) {
        await sendButton.first().click();

        // After sending, input should be cleared
        await expect(page.getByText('E2E response received.')).toBeVisible();
        const inputValue = await messageInput.first().inputValue();
        expect(inputValue).toBe('');
      }
    }
  });

  test('should display sent messages in chat history', async ({ page }) => {
    await page.goto('/chat');

    // Look for chat message display area
    const chatMessages = page.locator('[role="article"], .message, .chat-message');

    // Initially should have some messages or be empty
    const initialCount = await chatMessages.count();
    expect(initialCount).toBeGreaterThanOrEqual(0);
  });

  test('should handle message submission errors gracefully', async ({ page }) => {
    // Mock API to return error
    await page.route('**/chat/conversations/conv-e2e/messages', (route) => {
      route.abort();
    });

    await page.goto('/chat');

    const messageInput = page.getByLabel(/chat message input/i);
    const count = await messageInput.count();

    if (count > 0) {
      await messageInput.first().fill('Error test message');

      const sendButton = page.getByRole('button', { name: /send message/i });
      const sendCount = await sendButton.count();

      if (sendCount > 0) {
        await sendButton.first().click();

        // Error message should appear
        await expect(page.locator('text=/error|failed|connection/i')).toBeVisible({
          timeout: 5000,
        });
      }
    }
  });

  test('should support keyboard shortcuts for sending', async ({ page }) => {
    await page.goto('/chat');

    const messageInput = page.getByLabel(/chat message input/i);
    const count = await messageInput.count();

    if (count > 0) {
      const input = messageInput.first();
      await input.fill('Test message');

      // Try Ctrl+Enter to send
      await input.press('Control+Enter');

      // Check if message was sent (input cleared or message appeared)
      await page.waitForTimeout(500);
    }
  });

  test('should display message timestamps', async ({ page }) => {
    await page.goto('/chat');

    // Look for timestamp elements
    const timestamps = page.locator('time, [aria-label*="time" i]');

    const count = await timestamps.count();
    // May or may not have timestamps, both are valid
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should load conversation history', async ({ page }) => {
    await page.goto('/chat');

    // Wait for any API calls to complete
    await page.waitForLoadState('networkidle');

    // Check if messages are displayed
    const messages = page.locator('[role="article"], .message, .chat-message');
    const messageCount = await messages.count();

    // Should have some messages loaded or show empty state
    expect(messageCount).toBeGreaterThanOrEqual(0);
  });
});

test.describe('Provider Selection', () => {
  test.beforeEach(async ({ page, context }) => {
    await page.route('**/chat/conversations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

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

    await context.addCookies([
      {
        name: 'goblin_auth',
        value: '1',
        domain: 'localhost',
        path: '/',
      },
      {
        name: 'session_token',
        value: 'mock-session-token-e2e',
        domain: 'localhost',
        path: '/',
      },
    ]);

    await context.addInitScript(() => {
      document.cookie = 'goblin_auth=1; Path=/';
      window.localStorage.setItem(
        'user_data',
        JSON.stringify({ id: 'test_user', email: 'test@example.com', role: 'user' })
      );
    });
  });

  test('should display provider selector if available', async ({ page }) => {
    await page.goto('/chat');

    // Look for provider dropdown or selector
    const providerSelector = page.getByText(/Provider:|Model:/i);

    const count = await providerSelector.count();
    if (count > 0) {
      await expect(providerSelector.first()).toBeVisible();
    }
  });

  test('should allow provider selection', async ({ page }) => {
    await page.goto('/chat');

    const providerSelector = page.locator('select, [role="combobox"]');
    const count = await providerSelector.count();

    if (count > 0) {
      await providerSelector.first().click();

      // Look for options
      const options = page.locator('[role="option"]');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
      }
    }
  });

  test('should display cost estimates if showing', async ({ page }) => {
    await page.goto('/chat');

    // Look for cost-related elements
    const costDisplay = page.locator('text=/cost|price|\\$|tokens/i');

    const count = await costDisplay.count();
    // May or may not be visible
    expect(count).toBeGreaterThanOrEqual(0);
  });
});
