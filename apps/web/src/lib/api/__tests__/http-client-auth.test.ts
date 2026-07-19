import MockAdapter from 'axios-mock-adapter';

vi.mock('../../supabase', () => ({
  authGetSession: vi.fn(async () => ({
    session: { access_token: 'supabase-jwt' },
  })),
  authRefreshSession: vi.fn(async () => ({
    session: { access_token: 'refreshed-supabase-jwt' },
  })),
  supabaseConfigured: true,
}));

import { authGetSession, authRefreshSession } from '../../supabase';
import { attachSupabaseInterceptor, frontendHttp } from '../http-client';
import { getFrontend, postFrontend } from '../http-helpers';

describe('Supabase auth transport', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(frontendHttp);
    vi.mocked(authGetSession).mockResolvedValue({
      session: { access_token: 'supabase-jwt' },
    } as Awaited<ReturnType<typeof authGetSession>>);
    vi.mocked(authRefreshSession).mockResolvedValue({
      session: { access_token: 'refreshed-supabase-jwt' },
    } as Awaited<ReturnType<typeof authRefreshSession>>);
  });

  afterEach(() => {
    mock.restore();
  });

  it('resolves the Supabase token before the first proxy request', async () => {
    mock.onGet('/api/settings/').reply((config) => {
      expect(config.headers?.Authorization).toBe('Bearer supabase-jwt');
      return [200, { success: true, data: { providers: [] } }];
    });

    await getFrontend('/api/settings/');
  });

  it('replaces a stale legacy token on conversation creation requests', async () => {
    document.cookie = 'session_token=legacy-stale; Path=/';
    mock.onPost('/api/chat/conversations').reply((config) => {
      expect(config.headers?.Authorization).toBe('Bearer supabase-jwt');
      return [200, { success: true, data: { conversation_id: 'conversation-1' } }];
    });

    await postFrontend(
      '/api/chat/conversations',
      { title: 'New conversation' },
      {
        headers: { Authorization: 'Bearer legacy-stale' },
      }
    );
  });

  it('adds the Supabase Bearer token to requests sent through the Next proxy', async () => {
    await attachSupabaseInterceptor();
    mock.onGet('/api/chat/conversations').reply(200, { success: true, data: [] });

    await frontendHttp.get('/api/chat/conversations');

    expect(mock.history.get[0]?.headers?.Authorization).toBe('Bearer supabase-jwt');
  });

  it('refreshes and retries a 401 from the Next proxy', async () => {
    mock.onPost('/api/chat/conversations').replyOnce(401, { detail: 'Not authenticated' });
    mock.onPost('/api/chat/conversations').reply((config) => {
      expect(config.headers?.Authorization).toBe('Bearer refreshed-supabase-jwt');
      return [200, { success: true, data: { conversation_id: 'conversation-1' } }];
    });

    await postFrontend('/api/chat/conversations', { title: 'New conversation' });

    expect(authRefreshSession).toHaveBeenCalledTimes(1);
    expect(mock.history.post).toHaveLength(2);
  });
});
