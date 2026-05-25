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

describe('api client consumer contracts', () => {
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
      }),
    );
  });

  it('pins /api/generate contract usage through frontend API path', async () => {
    frontendPostMock.mockResolvedValue({
      data: { content: 'ok', choices: [{ message: { content: 'ok' } }] },
    });

    const { apiClient } = await import('@/api');
    const content = await apiClient.chatCompletion([{ role: 'user', content: 'hello' }]);

    expect(content).toBe('ok');
    expect(frontendPostMock).toHaveBeenCalledWith('/api/generate', {
      messages: [{ role: 'user', content: 'hello' }],
      model: undefined,
    }, undefined);
  });
});
