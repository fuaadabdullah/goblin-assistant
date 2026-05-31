/**
 * Token-refresh interceptor tests.
 *
 * The backendHttp axios instance has a response interceptor that:
 * 1. Catches 401 responses
 * 2. Calls /auth/refresh once (deduped with a lock)
 * 3. Retries the original request with the new token
 * 4. Falls through on /auth/refresh 401 (no infinite loop)
 */

// Must be hoisted before any imports so shared.ts picks up the mocks
jest.mock('../../../utils/auth-session', () => ({
  getRefreshToken: jest.fn(() => 'refresh-token-abc'),
  getAuthToken: jest.fn(() => null),
  persistAuthSession: jest.fn(),
  clearAuthSession: jest.fn(),
}));

import MockAdapter from 'axios-mock-adapter';
import { backendHttp, refreshAccessToken } from '../shared';
import * as authSession from '../../../utils/auth-session';

const mockGetRefreshToken = authSession.getRefreshToken as jest.MockedFunction<
  typeof authSession.getRefreshToken
>;
const mockPersistAuthSession = authSession.persistAuthSession as jest.MockedFunction<
  typeof authSession.persistAuthSession
>;
const mockClearAuthSession = authSession.clearAuthSession as jest.MockedFunction<
  typeof authSession.clearAuthSession
>;

let mock: MockAdapter;

beforeEach(() => {
  mock = new MockAdapter(backendHttp);
  jest.clearAllMocks();
  mockGetRefreshToken.mockReturnValue('refresh-token-abc');
});

afterEach(() => {
  mock.restore();
});

// ---- refreshAccessToken ----------------------------------------------------

describe('refreshAccessToken', () => {
  it('returns new access token and persists session on success', async () => {
    mock.onPost('/auth/refresh').reply(200, {
      access_token: 'new-jwt',
      refresh_token: 'new-refresh',
      expires_in: 3600,
      user: { id: 'u1', email: 'test@example.com' },
    });

    const token = await refreshAccessToken();

    expect(token).toBe('new-jwt');
    expect(mockPersistAuthSession).toHaveBeenCalledWith(
      expect.objectContaining({ token: 'new-jwt' })
    );
  });

  it('returns null and clears session when refresh endpoint returns 401', async () => {
    mock.onPost('/auth/refresh').reply(401, { detail: 'refresh token expired' });

    const token = await refreshAccessToken();

    expect(token).toBeNull();
    expect(mockClearAuthSession).toHaveBeenCalled();
  });

  it('returns null when response body has no access_token', async () => {
    mock.onPost('/auth/refresh').reply(200, { access_token: null });

    const token = await refreshAccessToken();

    expect(token).toBeNull();
  });

  it('returns null and clears session on network error', async () => {
    mock.onPost('/auth/refresh').networkError();

    const token = await refreshAccessToken();

    expect(token).toBeNull();
    expect(mockClearAuthSession).toHaveBeenCalled();
  });
});

// ---- 401 interceptor -------------------------------------------------------

describe('backendHttp 401 interceptor', () => {
  it('retries original request after successful token refresh', async () => {
    mock.onPost('/auth/refresh').reply(200, {
      access_token: 'refreshed-jwt',
      expires_in: 3600,
    });
    mock
      .onGet('/api/protected')
      .replyOnce(401, { detail: 'Unauthorized' })
      .onGet('/api/protected')
      .reply(200, { data: 'secret' });

    const response = await backendHttp.get('/api/protected');

    expect(response.status).toBe(200);
    expect(response.data).toEqual({ data: 'secret' });
  });

  it('does NOT retry /auth/refresh on 401 (prevents infinite loop)', async () => {
    mock.onPost('/auth/refresh').reply(401, { detail: 'Refresh token expired' });

    await expect(backendHttp.post('/auth/refresh', {})).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(mock.history.post.filter((r) => r.url === '/auth/refresh')).toHaveLength(1);
  });

  it('does NOT retry a request a second time (_retry flag)', async () => {
    mock.onPost('/auth/refresh').reply(200, { access_token: 'new-jwt', expires_in: 3600 });
    mock.onGet('/api/protected').reply(401, { detail: 'Unauthorized' });

    await expect(backendHttp.get('/api/protected')).rejects.toMatchObject({
      response: { status: 401 },
    });
    // Refresh attempted once
    expect(mock.history.post.filter((r) => r.url === '/auth/refresh')).toHaveLength(1);
    // Endpoint hit twice: original + one retry
    expect(mock.history.get.filter((r) => r.url === '/api/protected')).toHaveLength(2);
  });

  it('propagates error when refresh returns no token', async () => {
    mock.onPost('/auth/refresh').reply(200, { access_token: null });
    mock.onGet('/api/protected').reply(401, { detail: 'Unauthorized' });

    await expect(backendHttp.get('/api/protected')).rejects.toMatchObject({
      response: { status: 401 },
    });
  });

  it('passes through non-401 errors without attempting refresh', async () => {
    mock.onGet('/api/data').reply(500, { detail: 'Internal Server Error' });

    await expect(backendHttp.get('/api/data')).rejects.toMatchObject({
      response: { status: 500 },
    });
    expect(mock.history.post.filter((r) => r.url === '/auth/refresh')).toHaveLength(0);
  });

  it('deduplicates concurrent refresh calls (only one /auth/refresh request)', async () => {
    let refreshCount = 0;
    mock.onPost('/auth/refresh').reply(() => {
      refreshCount++;
      return [200, { access_token: `token-${refreshCount}`, expires_in: 3600 }];
    });
    mock
      .onGet('/api/a')
      .replyOnce(401, { detail: 'Unauthorized' })
      .onGet('/api/a')
      .reply(200, { ok: true });
    mock
      .onGet('/api/b')
      .replyOnce(401, { detail: 'Unauthorized' })
      .onGet('/api/b')
      .reply(200, { ok: true });

    await Promise.all([backendHttp.get('/api/a'), backendHttp.get('/api/b')]);

    expect(refreshCount).toBe(1);
  });
});
