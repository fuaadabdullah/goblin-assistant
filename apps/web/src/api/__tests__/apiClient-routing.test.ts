import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';

const backendGetMock = vi.fn();
const backendPostMock = vi.fn();
const backendPutMock = vi.fn();
const backendPatchMock = vi.fn();
const frontendGetMock = vi.fn();
const frontendPostMock = vi.fn();

vi.mock('axios', () => {
  const create = vi.fn();
  const axios = { create, isAxiosError: vi.fn(() => false) };
  return { __esModule: true, default: axios, create, isAxiosError: axios.isAxiosError };
});

describe('apiClient.getRoutingInfo', () => {
  const originalEnv = process.env;

  beforeEach(async () => {
    vi.resetModules();
    vi.clearAllMocks();
    const { default: axios } = await import('axios');
    vi.mocked(axios.create)
      .mockImplementationOnce(() => ({
        interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
        get: backendGetMock,
        post: backendPostMock,
        put: backendPutMock,
        patch: backendPatchMock,
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

  it('calls /routing/info on the configured backend base URL', async () => {
    backendGetMock.mockResolvedValue({ data: { status: 'ok' } });

    const { apiClient } = await import('@/api');
    await apiClient.getRoutingInfo();

    expect(backendGetMock).toHaveBeenCalledTimes(1);
    expect(backendGetMock.mock.calls[0][0]).toBe('/api/v1/routing/info');
  });
});
