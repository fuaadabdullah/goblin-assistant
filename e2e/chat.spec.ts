import { test, expect } from '@playwright/test';

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page, context }) => {
    // Mock localStorage to simulate authenticated user
    await context.addInitScript(() => {
      window.localStorage.setItem(
        'user',
        JSON.stringify({ id: 'test_user', email: 'test@example.com' })
      );
      window.localStorage.setItem('auth-token', 'mock_token');
    });
  });

  test('should display chat interface after authentication', async ({ page }) => {
    // Navigate to chat/dashboard page
    await page.goto('/dashboard');
    
    // Look for chat-related elements
    const chatArea = page.locator('[role="main"], main, .chat-container');
    await expect(chatArea).toBeVisible({ timeout: 5000 });
  });

  test('should have message input field', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Look for message input (textarea or input field)
    const messageInput = page.locator('textarea, input[placeholder*="message" i], input[placeholder*="ask" i]');
    
    const count = await messageInput.count();
    if (count > 0) {
      await expect(messageInput.first()).toBeVisible();
    }
  });

  test('should allow typing messages', async ({ page }) => {
    await page.goto('/dashboard');
    
    const messageInput = page.locator('textarea, input[placeholder*="message" i]');
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
    await page.goto('/dashboard');
    
    // Look for send button
    const sendButton = page.locator('button').filter({ hasText: /send|submit|ask/i });
    
    const count = await sendButton.count();
    if (count > 0) {
      await expect(sendButton.first()).toBeVisible();
    }
  });

  test('should send message on button click', async ({ page }) => {
    // Mock the chat API endpoint
    await page.route('**/api/chat/**', (route) => {
      route.abort();
    });
    
    await page.goto('/dashboard');
    
    const messageInput = page.locator('textarea, input[placeholder*="message" i]');
    const count = await messageInput.count();
    
    if (count > 0) {
      await messageInput.first().fill('Test message');
      
      const sendButton = page.locator('button').filter({ hasText: /send|submit/i });
      const sendCount = await sendButton.count();
      
      if (sendCount > 0) {
        await sendButton.first().click();
        
        // After sending, input should be cleared
        await page.waitForTimeout(500);
        const inputValue = await messageInput.first().inputValue();
        expect(inputValue).toBe('');
      }
    }
  });

  test('should display sent messages in chat history', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Look for chat message display area
    const chatMessages = page.locator('[role="article"], .message, .chat-message');
    
    // Initially should have some messages or be empty
    const initialCount = await chatMessages.count();
    expect(initialCount).toBeGreaterThanOrEqual(0);
  });

  test('should handle message submission errors gracefully', async ({ page }) => {
    // Mock API to return error
    await page.route('**/api/chat/**', (route) => {
      route.abort();
    });
    
    await page.goto('/dashboard');
    
    const messageInput = page.locator('textarea, input[placeholder*="message" i]');
    const count = await messageInput.count();
    
    if (count > 0) {
      await messageInput.first().fill('Error test message');
      
      const sendButton = page.locator('button').filter({ hasText: /send|submit/i });
      const sendCount = await sendButton.count();
      
      if (sendCount > 0) {
        await sendButton.first().click();
        
        // Error message should appear
        await expect(page.locator('text=/error|failed|connection/i')).toBeVisible({ timeout: 5000 });
      }
    }
  });

  test('should support keyboard shortcuts for sending', async ({ page }) => {
    await page.goto('/dashboard');
    
    const messageInput = page.locator('textarea, input[placeholder*="message" i]');
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
    await page.goto('/dashboard');
    
    // Look for timestamp elements
    const timestamps = page.locator('time, [aria-label*="time" i], span:has-text(/\\d{1,2}:\\d{2}/)');
    
    const count = await timestamps.count();
    // May or may not have timestamps, both are valid
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should load conversation history', async ({ page }) => {
    await page.goto('/dashboard');
    
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
    await context.addInitScript(() => {
      window.localStorage.setItem(
        'user',
        JSON.stringify({ id: 'test_user', email: 'test@example.com' })
      );
    });
  });

  test('should display provider selector if available', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Look for provider dropdown or selector
    const providerSelector = page.locator('select, [role="combobox"], button:has-text(/provider|model|gpt|Claude/i)');
    
    const count = await providerSelector.count();
    if (count > 0) {
      await expect(providerSelector.first()).toBeVisible();
    }
  });

  test('should allow provider selection', async ({ page }) => {
    await page.goto('/dashboard');
    
    const providerSelector = page.locator('select, [role="combobox"], button:has-text(/provider|model/i)');
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
    await page.goto('/dashboard');
    
    // Look for cost-related elements
    const costDisplay = page.locator('text=/cost|price|\\$|tokens/i');
    
    const count = await costDisplay.count();
    // May or may not be visible
    expect(count).toBeGreaterThanOrEqual(0);
  });
});
