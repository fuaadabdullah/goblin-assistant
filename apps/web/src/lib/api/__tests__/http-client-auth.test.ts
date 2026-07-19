import MockAdapter from 'axios-mock-adapter';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../supabase', () => ({
  authGetSession: vi.fn(),
  authRefreshSession: vi.fn(),
  supabaseConfigured: true,
}));

import { authGetSession, authRefreshSession } from '../../supabase';
import { frontendHttp } from '../http-client';
import { getFrontend, postFrontend } from '../http-helpers';

describe('frontend HTTP authentication', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(frontendHttp);
    vi.mocked(authGetSession).mockResolvedValue({ session: { access_token: 'supabase-jwt' } } as never);
    vi.mocked(authRefreshSession).mockResolvedValue({
      session: { access_token: 'refreshed-supabase-jwt' },
    } as never);
  });

  afterEach(() => {
    mock.restore();
    vi.clearAllMocks();
  });

  it('sends the Supabase bearer token through the Next.js proxy before React auth bootstrap', async () => {
    mock.onPost('/api/chat/conversations').reply((config) => {
      expect(config.headers?.Authorization).toBe('Bearer supabase-jwt');
      return [200, { conversation_id: 'conversation-1' }];
    });

    await expect(postFrontend('/api/chat/conversations', {})).resolves.toEqual({
      conversation_id: 'conversation-1',
    });
  });

  it('resolves the Supabase token before the first settings request', async () => {
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

  it('refreshes and retries an expired proxy request once', async () => {
    let attempts = 0;
    mock.onPost('/api/chat/conversations').reply((config) => {
      attempts += 1;
      if (attempts === 1) return [401, { detail: 'Not authenticated' }];
      expect(config.headers?.Authorization).toBe('Bearer refreshed-supabase-jwt');
      return [200, { conversation_id: 'conversation-2' }];
    });

    await expect(postFrontend('/api/chat/conversations', {})).resolves.toEqual({
      conversation_id: 'conversation-2',
    });
    expect(authRefreshSession).toHaveBeenCalledTimes(1);
    expect(attempts).toBe(2);
  });
});
