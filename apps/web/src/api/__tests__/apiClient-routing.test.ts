import { beforeEach, afterEach, describe, expect, it, jest } from '@jest/globals';

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

describe('apiClient.getRoutingInfo', () => {
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

  it('calls /routing/info on the configured backend base URL', async () => {
    backendGetMock.mockResolvedValue({ data: { status: 'ok' } });

    const { apiClient } = await import('@/api');
    await apiClient.getRoutingInfo();

    expect(backendGetMock).toHaveBeenCalledTimes(1);
    expect(backendGetMock.mock.calls[0][0]).toBe('/routing/info');
  });
});
