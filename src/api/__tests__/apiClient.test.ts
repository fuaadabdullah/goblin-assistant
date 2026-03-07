import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';

jest.mock('../../utils/auth-session', () => ({
  getAuthToken: jest.fn(() => 'session-token-123'),
}));

describe('apiClient chat conversations', () => {
  const originalFetch = global.fetch;
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = {
      ...originalEnv,
      NEXT_PUBLIC_API_BASE_URL: 'https://backend.example',
      NEXT_PUBLIC_BACKEND_URL: 'https://backend.example',
      NEXT_PUBLIC_FASTAPI_URL: 'https://backend.example',
    };
  });

  afterEach(() => {
    process.env = originalEnv;
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('maps backend createConversation responses and sends bearer auth', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        conversation_id: 'conv-backend-1',
        title: 'Persisted',
        created_at: '2026-03-07T12:00:00.000Z',
      }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    const { apiClient } = await import('../apiClient');
    const created = await apiClient.createConversation('Persisted');

    expect(created).toEqual({
      conversationId: 'conv-backend-1',
      title: 'Persisted',
      createdAt: '2026-03-07T12:00:00.000Z',
    });
    expect(fetchMock).toHaveBeenCalledWith(
      'https://backend.example/chat/conversations',
      expect.objectContaining({
        method: 'POST',
      })
    );

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.headers).toBeInstanceOf(Headers);
    const headers = init.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer session-token-123');
  });
});
