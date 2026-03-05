type MockReq = {
  method: string;
  headers: Record<string, string | string[] | undefined>;
};

type MockRes = {
  statusCode: number;
  body: unknown;
  headers: Record<string, string>;
  setHeader: (key: string, value: string) => void;
  status: (code: number) => MockRes;
  json: (payload: unknown) => MockRes;
};

type FetchResponseInit = {
  status: number;
  body?: unknown;
  headers?: Record<string, string>;
};

function createReq(overrides: Partial<MockReq> = {}): MockReq {
  return {
    method: 'GET',
    headers: {},
    ...overrides,
  };
}

function createRes(): MockRes {
  return {
    statusCode: 200,
    body: null,
    headers: {},
    setHeader(key: string, value: string) {
      this.headers[key.toLowerCase()] = value;
    },
    status(code: number) {
      this.statusCode = code;
      return this;
    },
    json(payload: unknown) {
      this.body = payload;
      return this;
    },
  };
}

function createFetchResponse({
  status,
  body = {},
  headers = {},
}: FetchResponseInit): Response {
  const normalizedHeaders = Object.fromEntries(
    Object.entries(headers).map(([k, v]) => [k.toLowerCase(), v]),
  );
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: {
      get: (name: string) => normalizedHeaders[name.toLowerCase()] ?? null,
    },
    json: async () => body,
  } as unknown as Response;
}

function loadHandler() {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  return require('../models').default as (
    req: MockReq,
    res: MockRes,
  ) => Promise<void>;
}

describe('/api/models thin proxy', () => {
  const originalFetch = global.fetch;
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
    delete process.env.INTERNAL_PROXY_API_KEY;
  });

  afterEach(() => {
    process.env = originalEnv;
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('proxies to backend /v1/providers/models with internal key', async () => {
    process.env.GOBLIN_BACKEND_URL = 'https://backend.example';
    process.env.INTERNAL_PROXY_API_KEY = 'proxy-key';

    const fetchMock = jest.fn().mockResolvedValue(
      createFetchResponse({
        status: 200,
        body: {
          models: [
            {
              name: 'qwen2.5:3b',
              provider: 'ollama_gcp',
              size: null,
              health: 'unknown',
              is_selectable: true,
              health_reason: null,
            },
          ],
          providers: [
            {
              id: 'ollama_gcp',
              health: 'unknown',
              configured: true,
              is_selectable: true,
              health_reason: null,
            },
          ],
          source: 'configured_with_health',
        },
        headers: {
          'x-correlation-id': 'cid-123',
        },
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq();
    const res = createRes();

    await handler(req, res);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe('https://backend.example/v1/providers/models');

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe('GET');
    expect((init.headers as Record<string, string>)['X-Internal-API-Key']).toBe('proxy-key');
    expect(res.statusCode).toBe(200);
    expect(res.headers['x-correlation-id']).toBe('cid-123');
    expect(res.body).toEqual({
      models: [
        {
          name: 'qwen2.5:3b',
          provider: 'ollama_gcp',
          size: null,
          health: 'unknown',
          is_selectable: true,
          health_reason: null,
        },
      ],
      providers: [
        {
          id: 'ollama_gcp',
          health: 'unknown',
          configured: true,
          is_selectable: true,
          health_reason: null,
        },
      ],
      source: 'configured_with_health',
    });
  });

  it('passes through empty registry responses', async () => {
    process.env.GOBLIN_BACKEND_URL = 'https://backend.example';

    const fetchMock = jest.fn().mockResolvedValue(
      createFetchResponse({
        status: 200,
        body: {
          models: [],
          source: 'empty',
        },
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq();
    const res = createRes();

    await handler(req, res);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(res.statusCode).toBe(200);
    expect(res.body).toEqual({
      models: [],
      source: 'empty',
    });
  });

  it('passes backend status/body through', async () => {
    process.env.GOBLIN_BACKEND_URL = 'https://backend.example';

    const fetchMock = jest.fn().mockResolvedValue(
      createFetchResponse({
        status: 503,
        body: { detail: 'Provider health check failed.' },
        headers: {
          'x-correlation-id': 'cid-503',
        },
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq();
    const res = createRes();

    await handler(req, res);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(res.statusCode).toBe(503);
    expect(res.body).toEqual({ detail: 'Provider health check failed.' });
    expect(res.headers['x-correlation-id']).toBe('cid-503');
  });

  it('maps transport errors to 502', async () => {
    process.env.GOBLIN_BACKEND_URL = 'https://backend.example';

    const fetchMock = jest.fn().mockRejectedValue(new Error('backend timeout'));
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq();
    const res = createRes();

    await handler(req, res);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(res.statusCode).toBe(502);
    expect(res.body).toEqual({ error: 'Backend unreachable' });
  });

  it('rejects non-GET methods', async () => {
    const fetchMock = jest.fn();
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq({ method: 'POST' });
    const res = createRes();

    await handler(req, res);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(res.statusCode).toBe(405);
    expect(res.body).toEqual({ error: 'Method not allowed' });
  });
});
