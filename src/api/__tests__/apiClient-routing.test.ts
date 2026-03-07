function createFetchResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response;
}

describe('apiClient.getRoutingInfo', () => {
  const originalFetch = global.fetch;
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = {
      ...originalEnv,
      NEXT_PUBLIC_API_BASE_URL: 'https://backend.example',
    };
  });

  afterEach(() => {
    process.env = originalEnv;
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('calls /routing/info on the configured backend base URL', async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValue(createFetchResponse(200, { status: 'ok' }));
    global.fetch = fetchMock as unknown as typeof fetch;

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { apiClient } = require('../apiClient') as typeof import('../apiClient');
    await apiClient.getRoutingInfo();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe('https://backend.example/routing/info');
  });
});
