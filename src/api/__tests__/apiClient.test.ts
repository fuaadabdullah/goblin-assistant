import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';

const backendGetMock = jest.fn();
const backendPostMock = jest.fn();
const backendPutMock = jest.fn();
const backendPatchMock = jest.fn();
const frontendGetMock = jest.fn();
const frontendPostMock = jest.fn();

jest.mock('axios', () => {
  const create = jest
    .fn()
    .mockImplementationOnce(() => ({
      interceptors: {
        response: { use: jest.fn() },
      },
      get: backendGetMock,
      post: backendPostMock,
      put: backendPutMock,
      patch: backendPatchMock,
    }))
    .mockImplementationOnce(() => ({
      get: frontendGetMock,
      post: frontendPostMock,
    }));

  const axios = {
    create,
    isAxiosError: jest.fn(() => false),
  };

  return {
    __esModule: true,
    default: axios,
    create,
    isAxiosError: axios.isAxiosError,
  };
});

jest.mock('../../utils/auth-session', () => ({
  getAuthToken: jest.fn(() => 'session-token-123'),
  getRefreshToken: jest.fn(() => null),
  persistAuthSession: jest.fn(),
  clearAuthSession: jest.fn(),
}));

describe('apiClient chat conversations', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
    process.env = {
      ...originalEnv,
      NEXT_PUBLIC_API_BASE_URL: 'https://backend.example',
      NEXT_PUBLIC_BACKEND_URL: 'https://backend.example',
      NEXT_PUBLIC_FASTAPI_URL: 'https://backend.example',
    };
  });

  afterEach(() => {
    process.env = originalEnv;
    jest.restoreAllMocks();
  });

  it('maps backend createConversation responses and sends bearer auth', async () => {
    backendPostMock.mockResolvedValue({
      data: {
        conversation_id: 'conv-backend-1',
        title: 'Persisted',
        created_at: '2026-03-07T12:00:00.000Z',
      },
    });

    const { apiClient } = await import('@/api');
    const created = await apiClient.createConversation('Persisted');

    expect(created).toEqual({
      conversationId: 'conv-backend-1',
      title: 'Persisted',
      createdAt: '2026-03-07T12:00:00.000Z',
    });
    expect(backendPostMock).toHaveBeenCalledWith(
      '/chat/conversations',
      { title: 'Persisted' },
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer session-token-123',
        }),
      }),
    );
  });
});
