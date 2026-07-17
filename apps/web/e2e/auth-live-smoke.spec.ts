import { expect, test, type Page } from '@playwright/test';

const liveAuthBackendUrl =
  process.env['LIVE_AUTH_BACKEND_URL']?.trim().replace(/\/+$/, '') || '';
const liveAuthEmail = process.env['LIVE_AUTH_EMAIL']?.trim() || '';
const liveAuthPassword = process.env['LIVE_AUTH_PASSWORD']?.trim() || '';
const liveAuthReady =
  Boolean(process.env['PLAYWRIGHT_TEST_BASE_URL']?.trim()) &&
  Boolean(liveAuthBackendUrl) &&
  Boolean(liveAuthEmail) &&
  Boolean(liveAuthPassword);

const liveAuthSkipReason =
  'Live auth smoke requires PLAYWRIGHT_TEST_BASE_URL, ' +
  'LIVE_AUTH_BACKEND_URL, LIVE_AUTH_EMAIL, and LIVE_AUTH_PASSWORD.';

const readBrowserAccessToken = async (page: Page): Promise<string | null> =>
  page.evaluate(() => {
    const extractAccessToken = (raw: string | null): string | null => {
      if (!raw) return null;

      const trimmed = raw.trim();
      if (/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(trimmed)) {
        return trimmed;
      }

      try {
        const parsed = JSON.parse(trimmed) as unknown;
        if (typeof parsed === 'string' && /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(parsed)) {
          return parsed;
        }

        const candidateQueue: unknown[] = [parsed];
        while (candidateQueue.length > 0) {
          const current = candidateQueue.pop();
          if (!current || typeof current !== 'object') continue;

          const currentRecord = current as Record<string, unknown>;
          const directToken = currentRecord['access_token'];
          if (typeof directToken === 'string' && directToken.trim()) {
            return directToken;
          }

          const session = currentRecord['session'];
          if (session && typeof session === 'object') candidateQueue.push(session);

          const currentSession = currentRecord['currentSession'];
          if (currentSession && typeof currentSession === 'object') {
            candidateQueue.push(currentSession);
          }

          const nestedData = currentRecord['data'];
          if (nestedData && typeof nestedData === 'object') {
            candidateQueue.push(nestedData);
          }
        }
      } catch {
        const match = trimmed.match(/"access_token"\s*:\s*"([^"]+)"/);
        if (match?.[1]) return match[1];
      }

      return null;
    };

    const storageBuckets = [window.localStorage, window.sessionStorage];
    for (const store of storageBuckets) {
      for (let index = 0; index < store.length; index += 1) {
        const key = store.key(index);
        if (!key) continue;
        const token = extractAccessToken(store.getItem(key));
        if (token) return token;
      }
    }

    const cookieEntries = document.cookie.split(';');
    for (const entry of cookieEntries) {
      const separatorIndex = entry.indexOf('=');
      const rawValue = separatorIndex >= 0 ? entry.slice(separatorIndex + 1) : '';
      const decodedValue = decodeURIComponent(rawValue.trim());
      const token = extractAccessToken(decodedValue);
      if (token) return token;
      if (/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(decodedValue)) {
        return decodedValue;
      }
    }

    return null;
  });

test.describe('Live auth smoke', () => {
  test.skip(!liveAuthReady, liveAuthSkipReason);

  test('logs in with email/password and reaches the protected backend', async ({
    page,
    request,
  }) => {
    await page.goto('/login?redirect=/chat');

    await expect(page.getByLabel(/email/i)).toBeVisible();
    await page.getByLabel(/email/i).fill(liveAuthEmail);
    await page.getByLabel(/^password$/i).fill(liveAuthPassword);
    await page.getByRole('button', { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/chat(?:[?#].*)?$/, { timeout: 90_000 });

    const accessToken = await readBrowserAccessToken(page);
    if (!accessToken) {
      throw new Error('Expected a Supabase session token in browser storage');
    }

    const response = await request.get(`${liveAuthBackendUrl}/api/v1/auth/me`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    expect(response.status()).toBe(200);

    const body = (await response.json()) as {
      success?: boolean;
      data?: { email?: string; id?: string };
    };

    expect(body.success).toBe(true);
    expect(body.data?.email).toBe(liveAuthEmail);
    expect(body.data?.id).toBeTruthy();
  });
});
