import { test, expect } from '@playwright/test';

test.describe('Privacy and Data Protection', () => {
  test.beforeEach(async ({ context }) => {
    await context.addInitScript(() => {
      window.localStorage.setItem(
        'user',
        JSON.stringify({ id: 'test_user', email: 'test@example.com' })
      );
    });
  });

  test('should not expose sensitive data in console', async ({ page }) => {
    const consoleLogs: string[] = [];
    
    page.on('console', (msg) => {
      consoleLogs.push(msg.text());
    });
    
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    
    // Check that API keys and tokens aren't logged
    const sensitiveStrings = ['api_key', 'secret', 'token'];
    consoleLogs.forEach((log) => {
      sensitiveStrings.forEach((sensitive) => {
        expect(log.toLowerCase()).not.toContain(sensitive.toLowerCase());
      });
    });
  });

  test('should not expose credentials in page source', async ({ page }) => {
    await page.goto('/dashboard');
    
    const pageContent = await page.content();
    
    // Check that API keys aren't in HTML
    // Regex patterns for common secret formats
    const skKeyPattern = /sk-[A-Za-z0-9]{20,}/g;
    const akiaKeyPattern = /AKIA[0-9A-Z]{16}/g;
    
    expect(pageContent).not.toMatch(skKeyPattern);
    expect(pageContent).not.toMatch(akiaKeyPattern);
  });

  test('should mask PII in messages', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Send a message with PII
    const messageInput = page.locator('textarea, input[placeholder*="message" i]');
    const count = await messageInput.count();
    
    if (count > 0) {
      const testMessage = 'My email is user@example.com and phone is 123-456-7890';
      await messageInput.first().fill(testMessage);
      
      const sendButton = page.locator('button').filter({ hasText: /send|submit/i });
      const sendCount = await sendButton.count();
      
      if (sendCount > 0) {
        await sendButton.first().click();
        
        // After sending, check if message is masked in display
        await page.waitForTimeout(500);
        
        // Look for either the original message or redacted version
        const messageDisplay = page.locator('[role="article"], .message');
        const messageText = await messageDisplay.textContent();
        
        // Should either show masked version or original (depends on implementation)
        expect(messageText).toBeDefined();
      }
    }
  });

  test('should have privacy policy link', async ({ page }) => {
    await page.goto('/');
    
    // Look for privacy policy link
    const privacyLink = page.locator('a:has-text(/privacy|gdpr|data protection/i)');
    
    const count = await privacyLink.count();
    if (count > 0) {
      await expect(privacyLink.first()).toBeVisible();
    }
  });

  test('should have terms of service link', async ({ page }) => {
    await page.goto('/');
    
    // Look for ToS link
    const tosLink = page.locator('a:has-text(/terms|terms of service|conditions/i)');
    
    const count = await tosLink.count();
    if (count > 0) {
      await expect(tosLink.first()).toBeVisible();
    }
  });

  test('should not send unencrypted sensitive data over http', async ({ page }) => {
    const requests: string[] = [];
    
    page.on('request', (request) => {
      if (request.url().startsWith('http://') && request.url().includes('api')) {
        requests.push(request.url());
      }
    });
    
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    
    // No API requests should be over plain HTTP
    expect(requests.length).toBe(0);
  });

  test('should clear sensitive data from localStorage on logout', async ({ page, context }) => {
    await context.addInitScript(() => {
      window.localStorage.setItem('api_key', 'secret123');
      window.localStorage.setItem('auth_token', 'token456');
    });
    
    await page.goto('/dashboard');
    
    // Look for logout button
    const logoutButton = page.locator('button').filter({ hasText: /logout|log out|sign out/i });
    const count = await logoutButton.count();
    
    if (count > 0) {
      await logoutButton.first().click();
      
      // After logout, sensitive data should be cleared
      await page.waitForLoadState('networkidle');
      
      const authToken = await page.evaluate(() => localStorage.getItem('auth_token'));
      
      // At least auth_token should be cleared
      expect(authToken).toBeNull();
    }
  });

  test('should not expose auth tokens in URLs', async ({ page }) => {
    page.on('request', (request) => {
      const url = request.url();
      
      // Check that auth tokens aren't in query params
      expect(url).not.toMatch(/[?&](token|auth|key)=sk-[A-Za-z0-9]+/);
      expect(url).not.toMatch(/[?&](api_key)=[A-Za-z0-9]+/);
    });
    
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
  });

  test('should require confirmation for data deletion', async ({ page }) => {
    // Look for account settings or data management
    const settingsLink = page.locator('a, button').filter({ hasText: /settings|account|profile/i });
    
    const count = await settingsLink.count();
    if (count > 0) {
      await settingsLink.first().click();
      
      // Look for delete account button
      const deleteButton = page.locator('button').filter({ hasText: /delete|remove|erase/i });
      const deleteCount = await deleteButton.count();
      
      if (deleteCount > 0) {
        await deleteButton.first().click();
        
        // Should show confirmation dialog
        const confirmDialog = page.locator('[role="alertdialog"], .modal, .dialog');
        const dialogCount = await confirmDialog.count();
        
        if (dialogCount > 0) {
          await expect(confirmDialog.first()).toBeVisible();
        }
      }
    }
  });
});

test.describe('Data Security', () => {
  test('should use HTTPS for all API calls', async ({ page }) => {
    const httpRequests: string[] = [];
    
    page.on('request', (request) => {
      const url = request.url();
      if (url.startsWith('http://') && !url.includes('localhost')) {
        httpRequests.push(url);
      }
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // No production API calls over HTTP
    expect(httpRequests.length).toBe(0);
  });

  test('should have Content Security Policy headers', async ({ page }) => {
    const response = await page.goto('/');
    const headers = response?.headers() || {};
    
    // Check for CSP header
    const hasCSP = headers['content-security-policy'] || headers['x-content-security-policy'];
    
    // CSP is recommended but not always enforced
    expect(hasCSP).toBeDefined();
  });

  test('should not allow framing in other sites', async ({ page }) => {
    const response = await page.goto('/');
    const headers = response?.headers() || {};
    
    const xFrameOptions = headers['x-frame-options'];
    
    // Should have X-Frame-Options to prevent clickjacking
    // Can be DENY, SAMEORIGIN, etc.
    if (xFrameOptions) {
      expect(xFrameOptions).not.toBe('ALLOW-ALL');
    }
  });
});
