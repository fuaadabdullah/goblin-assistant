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
  const axios = { create, isAxiosError: vi.fn(() => false) };
  return { __esModule: true, default: axios, create, isAxiosError: axios.isAxiosError };
});

describe('api client consumer contracts', () => {
  const originalEnv = process.env;

  beforeEach(async () => {
    vi.resetModules();
    vi.clearAllMocks();
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
      .mockImplementationOnce(() => ({ get: frontendGetMock, post: frontendPostMock }));
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

  it('pins routing contract shape for startup dependency', async () => {
    backendGetMock.mockResolvedValue({
      data: {
        status: 'ok',
        default_provider: 'openai',
        available_providers: ['openai', 'anthropic'],
      },
    });

    const { apiClient } = await import('@/api');
    const payload = await apiClient.getRoutingInfo();

    expect(payload).toEqual(
      expect.objectContaining({
        status: 'ok',
        default_provider: 'openai',
      })
    );
  });

  it('pins /api/generate contract usage through frontend API path', async () => {
    frontendPostMock.mockResolvedValue({
      data: { content: 'ok', choices: [{ message: { content: 'ok' } }] },
    });

    const { apiClient } = await import('@/api');
    const content = await apiClient.chatCompletion([{ role: 'user', content: 'hello' }]);

    expect(content).toBe('ok');
    expect(frontendPostMock).toHaveBeenCalledWith(
      '/api/generate',
      {
        messages: [{ role: 'user', content: 'hello' }],
        model: undefined,
      },
      undefined
    );
  });

  it('preserves legacy api shim methods over backend helpers', async () => {
    backendGetMock.mockResolvedValue({ data: { ok: 'get' } });
    backendPostMock.mockResolvedValue({ data: { ok: 'post' } });
    backendPutMock.mockResolvedValue({ data: { ok: 'put' } });
    backendPatchMock.mockResolvedValue({ data: { ok: 'patch' } });
    backendDeleteMock.mockResolvedValue({ data: { ok: 'delete' } });

    const { api } = await import('@/api');

    await expect(api.get('/health')).resolves.toEqual({ data: { ok: 'get' } });
    await expect(api.post('/items', { id: 1 })).resolves.toEqual({ data: { ok: 'post' } });
    await expect(api.put('/items/1', { id: 1 })).resolves.toEqual({ data: { ok: 'put' } });
    await expect(api.patch('/items/1', { id: 2 })).resolves.toEqual({ data: { ok: 'patch' } });
    await expect(api.delete('/items/1')).resolves.toEqual({ data: { ok: 'delete' } });
  });
});
