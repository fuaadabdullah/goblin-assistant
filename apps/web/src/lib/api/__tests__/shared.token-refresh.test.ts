/**
 * Token-refresh interceptor tests.
 *
 * The backendHttp axios instance has a response interceptor that:
 * 1. Catches 401 responses
 * 2. Calls refreshAccessToken() once (deduped with a lock)
 * 3. Retries the original request with the new token
 * 4. Falls through on failed/absent refresh (no infinite loop)
 *
 * Per ADR-0006, refreshAccessToken() is Supabase-only — see
 * `docs/decisions/2026-07-17-supabase-only-auth.md`. The basic "attach
 * token" / "retry after successful refresh" paths are covered by
 * http-client-auth.test.ts; this file covers the remaining interceptor
 * edge cases (auth-endpoint exclusion, no-double-retry, dedup, error
 * propagation) plus refreshAccessToken()/refreshAccessTokenViaSupabase()
 * directly.
 */

vi.mock('../../supabase', () => ({
  authGetSession: vi.fn(),
  authRefreshSession: vi.fn(),
  supabaseConfigured: true,
}));

import MockAdapter from 'axios-mock-adapter';
import { backendHttp, frontendHttp, refreshAccessToken, refreshAccessTokenViaSupabase } from '../http-client';
import { authGetSession, authRefreshSession } from '../../supabase';

const mockAuthGetSession = authGetSession as vi.MockedFunction<typeof authGetSession>;
const mockAuthRefreshSession = authRefreshSession as vi.MockedFunction<typeof authRefreshSession>;

let mock: MockAdapter;
let frontendMock: MockAdapter;

beforeEach(() => {
  mock = new MockAdapter(backendHttp);
  frontendMock = new MockAdapter(frontendHttp);
  vi.clearAllMocks();
  mockAuthGetSession.mockResolvedValue({
    session: { access_token: 'existing-jwt' },
  } as Awaited<ReturnType<typeof authGetSession>>);
  mockAuthRefreshSession.mockResolvedValue({
    session: { access_token: 'refreshed-jwt' },
  } as Awaited<ReturnType<typeof authRefreshSession>>);
});

afterEach(() => {
  mock.restore();
  frontendMock.restore();
});

// ---- refreshAccessToken / refreshAccessTokenViaSupabase --------------------

describe('refreshAccessTokenViaSupabase', () => {
  it('returns the refreshed access token when a session already exists', async () => {
    const token = await refreshAccessTokenViaSupabase();

    expect(token).toBe('refreshed-jwt');
    expect(mockAuthRefreshSession).toHaveBeenCalledOnce();
  });

  it('returns null without attempting a refresh when there is no existing session', async () => {
    mockAuthGetSession.mockResolvedValue({ session: null } as Awaited<
      ReturnType<typeof authGetSession>
    >);

    const token = await refreshAccessTokenViaSupabase();

    expect(token).toBeNull();
    expect(mockAuthRefreshSession).not.toHaveBeenCalled();
  });

  it('returns null when the refreshed session has no access token', async () => {
    mockAuthRefreshSession.mockResolvedValue({ session: null } as Awaited<
      ReturnType<typeof authRefreshSession>
    >);

    const token = await refreshAccessTokenViaSupabase();

    expect(token).toBeNull();
  });
});

describe('refreshAccessToken', () => {
  it('delegates to refreshAccessTokenViaSupabase', async () => {
    const token = await refreshAccessToken();

    expect(token).toBe('refreshed-jwt');
  });
});

// ---- 401 interceptor -------------------------------------------------------

describe('backendHttp 401 interceptor', () => {
  it('retries original request after successful token refresh', async () => {
    mock
      .onGet('/api/protected')
      .replyOnce(401, { detail: 'Unauthorized' })
      .onGet('/api/protected')
      .reply(200, { data: 'secret' });

    const response = await backendHttp.get('/api/protected');

    expect(response.status).toBe(200);
    expect(response.data).toEqual({ data: 'secret' });
  });

  it('does NOT retry auth endpoints on 401 (prevents infinite loop)', async () => {
    mock.onPost('/api/auth/login').reply(401, { detail: 'Invalid credentials' });

    await expect(backendHttp.post('/api/auth/login', {})).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(mockAuthRefreshSession).not.toHaveBeenCalled();
  });

  it('does NOT retry a request a second time (_retry flag)', async () => {
    mock.onGet('/api/protected').reply(401, { detail: 'Unauthorized' });

    await expect(backendHttp.get('/api/protected')).rejects.toMatchObject({
      response: { status: 401 },
    });
    // Refresh attempted once
    expect(mockAuthRefreshSession).toHaveBeenCalledOnce();
    // Endpoint hit twice: original + one retry
    expect(mock.history.get.filter((r) => r.url === '/api/protected')).toHaveLength(2);
  });

  it('propagates error when refresh returns no token', async () => {
    mockAuthRefreshSession.mockResolvedValue({ session: null } as Awaited<
      ReturnType<typeof authRefreshSession>
    >);
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
    expect(mockAuthRefreshSession).not.toHaveBeenCalled();
  });

  it('deduplicates concurrent refresh calls (only one Supabase refresh call)', async () => {
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

    expect(mockAuthRefreshSession).toHaveBeenCalledOnce();
  });
});
