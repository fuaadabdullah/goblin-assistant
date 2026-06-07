import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const backendGetMock = vi.fn();
const backendPostMock = vi.fn();
const backendPutMock = vi.fn();
const backendPatchMock = vi.fn();
const backendDeleteMock = vi.fn();
const frontendGetMock = vi.fn();
const frontendPostMock = vi.fn();

vi.mock('axios', () => {
  const create = vi.fn();
  const axios = {
    create,
    isAxiosError: vi.fn(() => false),
  };
  return {
    __esModule: true,
    default: axios,
    create,
    isAxiosError: axios.isAxiosError,
  };
});

vi.mock('../../utils/auth-session', () => ({
  getAuthToken: vi.fn(() => 'session-token-123'),
  getRefreshToken: vi.fn(() => null),
  persistAuthSession: vi.fn(),
  clearAuthSession: vi.fn(),
}));

describe('apiClient chat conversations', () => {
  const originalEnv = process.env;

  beforeEach(async () => {
    vi.resetModules();
    vi.clearAllMocks();
    // Re-apply per-call implementations after clearAllMocks
    const { default: axios } = await import('axios');
    vi.mocked(axios.create)
      .mockImplementationOnce(() => ({
        interceptors: { response: { use: vi.fn() } },
        get: backendGetMock,
        post: backendPostMock,
        put: backendPutMock,
        patch: backendPatchMock,
        delete: backendDeleteMock,
      }))
      .mockImplementationOnce(() => ({
        get: frontendGetMock,
        post: frontendPostMock,
      }));
    process.env = {
      ...originalEnv,
      NEXT_PUBLIC_API_BASE_URL: 'https://backend.example',
      NEXT_PUBLIC_BACKEND_URL: 'https://backend.example',
      NEXT_PUBLIC_FASTAPI_URL: 'https://backend.example',
    };
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.restoreAllMocks();
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
      '/api/v1/chat/conversations',
      { title: 'Persisted' },
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer session-token-123',
        }),
      })
    );
  });

  it('routes legacy api.delete through the backend DELETE helper', async () => {
    backendDeleteMock.mockResolvedValue({ data: { deleted: true } });

    const { api } = await import('@/api');
    const result = await api.delete<{ deleted: boolean }>('/api/notifications/123');

    expect(result).toEqual({ data: { deleted: true } });
    expect(backendDeleteMock).toHaveBeenCalledWith('/api/notifications/123', undefined);
  });
});
