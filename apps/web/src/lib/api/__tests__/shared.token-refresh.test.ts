/**
 * Token-refresh interceptor tests.
 *
 * The backendHttp axios instance has a response interceptor that:
 * 1. Catches 401 responses
 * 2. Calls the internal auth refresh route once (deduped with a lock)
 * 3. Retries the original request with the new token
 * 4. Falls through on internal auth refresh 401 (no infinite loop)
 */

// Must be hoisted before any imports so shared.ts picks up the mocks
vi.mock('../../../utils/auth-session', () => ({
  getRefreshToken: vi.fn(() => 'refresh-token-abc'),
  getAuthToken: vi.fn(() => null),
  persistAuthSession: vi.fn(),
  clearAuthSession: vi.fn(),
}));

import MockAdapter from 'axios-mock-adapter';
import { backendHttp, frontendHttp, refreshAccessToken } from '../shared';
import * as authSession from '../../../utils/auth-session';

const mockGetRefreshToken = authSession.getRefreshToken as vi.MockedFunction<
  typeof authSession.getRefreshToken
>;
const mockPersistAuthSession = authSession.persistAuthSession as vi.MockedFunction<
  typeof authSession.persistAuthSession
>;
const mockClearAuthSession = authSession.clearAuthSession as vi.MockedFunction<
  typeof authSession.clearAuthSession
>;

let mock: MockAdapter;
let frontendMock: MockAdapter;

beforeEach(() => {
  mock = new MockAdapter(backendHttp);
  frontendMock = new MockAdapter(frontendHttp);
  vi.clearAllMocks();
  mockGetRefreshToken.mockReturnValue('refresh-token-abc');
});

afterEach(() => {
  mock.restore();
  frontendMock.restore();
});

// ---- refreshAccessToken ----------------------------------------------------

describe('refreshAccessToken', () => {
  it('returns new access token and persists session on success', async () => {
    frontendMock.onPost('/api/auth/refresh').reply(200, {
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
    frontendMock.onPost('/api/auth/refresh').reply(401, { detail: 'refresh token expired' });

    const token = await refreshAccessToken();

    expect(token).toBeNull();
    expect(mockClearAuthSession).toHaveBeenCalled();
  });

  it('returns null when response body has no access_token', async () => {
    frontendMock.onPost('/api/auth/refresh').reply(200, { access_token: null });

    const token = await refreshAccessToken();

    expect(token).toBeNull();
  });

  it('returns null and clears session on network error', async () => {
    frontendMock.onPost('/api/auth/refresh').networkError();

    const token = await refreshAccessToken();

    expect(token).toBeNull();
    expect(mockClearAuthSession).toHaveBeenCalled();
  });
});

// ---- 401 interceptor -------------------------------------------------------

describe('backendHttp 401 interceptor', () => {
  it('retries original request after successful token refresh', async () => {
    frontendMock.onPost('/api/auth/refresh').reply(200, {
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

  it('does NOT retry /api/auth/refresh on 401 (prevents infinite loop)', async () => {
    frontendMock.onPost('/api/auth/refresh').reply(401, { detail: 'Refresh token expired' });

    await expect(frontendHttp.post('/api/auth/refresh', {})).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(frontendMock.history.post.filter((r) => r.url === '/api/auth/refresh')).toHaveLength(1);
  });

  it('does NOT retry a request a second time (_retry flag)', async () => {
    frontendMock.onPost('/api/auth/refresh').reply(200, { access_token: 'new-jwt', expires_in: 3600 });
    mock.onGet('/api/protected').reply(401, { detail: 'Unauthorized' });

    await expect(backendHttp.get('/api/protected')).rejects.toMatchObject({
      response: { status: 401 },
    });
    // Refresh attempted once
    expect(frontendMock.history.post.filter((r) => r.url === '/api/auth/refresh')).toHaveLength(1);
    // Endpoint hit twice: original + one retry
    expect(mock.history.get.filter((r) => r.url === '/api/protected')).toHaveLength(2);
  });

  it('propagates error when refresh returns no token', async () => {
    frontendMock.onPost('/api/auth/refresh').reply(200, { access_token: null });
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
    expect(frontendMock.history.post.filter((r) => r.url === '/api/auth/refresh')).toHaveLength(0);
  });

  it('deduplicates concurrent refresh calls (only one /api/auth/refresh request)', async () => {
    let refreshCount = 0;
    frontendMock.onPost('/api/auth/refresh').reply(() => {
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
