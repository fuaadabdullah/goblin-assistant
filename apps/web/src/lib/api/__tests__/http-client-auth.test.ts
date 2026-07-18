import MockAdapter from 'axios-mock-adapter';

vi.mock('../../supabase', () => ({
  authGetSession: vi.fn(async () => ({
    session: { access_token: 'supabase-jwt' },
  })),
}));

import { attachSupabaseInterceptor, frontendHttp } from '../http-client';
import { getFrontend } from '../http-helpers';

describe('Supabase auth transport', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(frontendHttp);
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

  it('adds the Supabase Bearer token to requests sent through the Next proxy', async () => {
    await attachSupabaseInterceptor();
    mock.onGet('/api/chat/conversations').reply(200, { success: true, data: [] });

    await frontendHttp.get('/api/chat/conversations');

    expect(mock.history.get[0]?.headers?.Authorization).toBe('Bearer supabase-jwt');
  });
});
