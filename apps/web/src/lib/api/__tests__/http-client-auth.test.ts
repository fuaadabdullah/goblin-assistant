import MockAdapter from 'axios-mock-adapter';

vi.mock('../../supabase', () => ({
  authGetSession: vi.fn(async () => ({
    session: { access_token: 'supabase-jwt' },
  })),
}));

import { attachSupabaseInterceptor, frontendHttp } from '../http-client';

describe('Supabase auth transport', () => {
  let mock: MockAdapter;

  beforeAll(async () => {
    await attachSupabaseInterceptor();
  });

  beforeEach(() => {
    mock = new MockAdapter(frontendHttp);
  });

  afterEach(() => {
    mock.restore();
  });

  it('adds the Supabase Bearer token to requests sent through the Next proxy', async () => {
    mock.onGet('/api/chat/conversations').reply(200, { success: true, data: [] });

    await frontendHttp.get('/api/chat/conversations');

    expect(mock.history.get[0]?.headers?.Authorization).toBe('Bearer supabase-jwt');
  });
});
