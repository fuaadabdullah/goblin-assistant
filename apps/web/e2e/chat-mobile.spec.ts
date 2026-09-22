import { test, expect } from '@playwright/test';
import { authenticateE2EUser, mockCommonApiRoutes } from './support/common-mocks';

// iPhone 14 / 15 logical viewport. See docs/ux/RESPONSIVE_TESTING.md.
test.use({ viewport: { width: 390, height: 844 } });

test.describe('Chat on a small screen', () => {
  test.beforeEach(async ({ page, context }) => {
    const nowIso = new Date().toISOString();
    await mockCommonApiRoutes(page);
    // Sets localStorage `goblin_e2e_auth`, which lib/auth-state.ts's
    // readE2eAuthSnapshot() requires before it will report a signed-in user.
    await authenticateE2EUser(context);

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
          conversation_id: 'conv-mobile',
          title: 'Mobile message',
          created_at: nowIso,
        }),
      });
    });

    await page.route('**/chat/conversations/conv-mobile/messages', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message_id: 'msg-mobile',
          response: 'Mobile response.',
          provider: 'mock',
          model: 'mock-model',
          timestamp: nowIso,
          usage: { input_tokens: 3, output_tokens: 4, total_tokens: 7 },
          cost_usd: 0.0001,
          correlation_id: 'corr-mobile',
        }),
      });
    });

    await page.goto('/chat');
    // Wait for the authenticated chat shell. Until `useAuthSession` resolves,
    // ChatView renders its signed-out preview branch, which is a document-flow
    // page that legitimately scrolls.
    await expect(page.getByLabel('Chat message input')).toBeVisible();
  });

  test('the message list owns scrolling, not the document', async ({ page }) => {
    const documentScrolls = await page.evaluate(
      () => document.documentElement.scrollHeight > window.innerHeight + 1
    );
    expect(documentScrolls).toBe(false);
  });

  test('chat header fits on a single compact row', async ({ page }) => {
    // <header> lives inside <main>, so it has no `banner` role — locate by tag.
    const box = await page.locator('header').first().boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeLessThanOrEqual(64);
  });

  test('composer and Send button are visible without scrolling', async ({ page }) => {
    const input = page.getByLabel('Chat message input');
    await expect(input).toBeVisible();

    const inputBox = await input.boundingBox();
    expect(inputBox).not.toBeNull();
    expect(inputBox!.y + inputBox!.height).toBeLessThanOrEqual(844);

    const sendBox = await page.getByLabel('Send message').boundingBox();
    expect(sendBox).not.toBeNull();
    expect(sendBox!.y + sendBox!.height).toBeLessThanOrEqual(844);
  });

  test('no floating chat control overlaps the composer', async ({ page }) => {
    // `exact` matters: Playwright's name matching is substring-based, so
    // 'Open Chat' would otherwise also match the header's 'Open chat panel'.
    await expect(page.getByRole('button', { name: 'Open Chat', exact: true })).toHaveCount(0);
  });

  test('no global status bar overlaps the composer', async ({ page }) => {
    await expect(page.getByText('GoblinOS')).toHaveCount(0);
  });

  test('does not overflow horizontally', async ({ page }) => {
    const overflows = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 1
    );
    expect(overflows).toBe(false);
  });

  test('primary chat actions stay reachable', async ({ page }) => {
    await expect(page.getByLabel('Open chat panel')).toBeVisible();
    await expect(page.getByLabel('Global Search')).toBeVisible();
    await expect(page.getByLabel('Chat message input')).toBeVisible();
  });
});
