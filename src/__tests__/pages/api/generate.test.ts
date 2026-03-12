type MockReq = {
  method: string;
  body?: unknown;
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
    method: 'POST',
    body: {},
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
  return require('../../../pages/api/generate').default as (
    req: MockReq,
    res: MockRes,
  ) => Promise<void>;
}

describe('/api/generate thin proxy', () => {
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

  it('maps payload to backend /api/chat shape and injects internal key + forwarded-for', async () => {
    process.env.GOBLIN_BACKEND_URL = 'https://backend.example';
    process.env.INTERNAL_PROXY_API_KEY = 'proxy-key';

    const body = {
      prompt: 'Do not mutate',
      provider: 'azure-openai',
      max_tokens: 9999,
      temperature: 7.5,
      nested: { keep: true },
    };

    const fetchMock = jest.fn().mockResolvedValue(
      createFetchResponse({
        status: 200,
        body: {
          content: 'ok',
          model: 'gpt-4o-mini',
          provider: 'azure_openai',
        },
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq({
      body,
      headers: { 'x-forwarded-for': '1.2.3.4' },
    });
    const res = createRes();

    await handler(req, res);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe('https://backend.example/api/chat');

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe('POST');
    expect((init.headers as Record<string, string>)['X-Internal-API-Key']).toBe('proxy-key');
    expect((init.headers as Record<string, string>)['X-Forwarded-For']).toBe('1.2.3.4');
    expect(JSON.parse(String(init.body))).toEqual({
      messages: [{ role: 'user', content: 'Do not mutate' }],
      provider: 'azure-openai',
    });
  });

  it('passes backend status/body/headers through', async () => {
    process.env.GOBLIN_BACKEND_URL = 'https://backend.example';

    const fetchMock = jest.fn().mockResolvedValue(
      createFetchResponse({
        status: 429,
        body: { detail: 'rate_limited' },
        headers: {
          'x-correlation-id': 'cid-429',
          'x-request-id': 'rid-429',
          'x-license-tier': 'pro',
        },
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq({ body: { prompt: 'hi' } });
    const res = createRes();

    await handler(req, res);

    expect(res.statusCode).toBe(429);
    expect(res.body).toEqual({ detail: 'rate_limited' });
    expect(res.headers['x-correlation-id']).toBe('cid-429');
    expect(res.headers['x-request-id']).toBe('rid-429');
    expect(res.headers['x-license-tier']).toBe('pro');
  });

  it('passes explicit-selection failures through (422)', async () => {
    process.env.GOBLIN_BACKEND_URL = 'https://backend.example';

    const fetchMock = jest.fn().mockResolvedValue(
      createFetchResponse({
        status: 422,
        body: { detail: { code: 'invalid_selection', message: 'Unknown model selection' } },
        headers: {
          'x-correlation-id': 'cid-422',
        },
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq({ body: { provider: 'openai', model: 'not-real' } });
    const res = createRes();

    await handler(req, res);

    expect(res.statusCode).toBe(422);
    expect(res.body).toEqual({
      detail: { code: 'invalid_selection', message: 'Unknown model selection' },
    });
    expect(res.headers['x-correlation-id']).toBe('cid-422');
  });

  it('maps backend transport errors to 502', async () => {
    process.env.GOBLIN_BACKEND_URL = 'https://backend.example';

    const fetchMock = jest.fn().mockRejectedValue(new Error('connect ETIMEDOUT'));
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq({ body: { prompt: 'hello' } });
    const res = createRes();

    await handler(req, res);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(res.statusCode).toBe(502);
    expect(res.body).toEqual({ error: 'Backend unreachable' });
  });

  it('rejects non-POST methods', async () => {
    const fetchMock = jest.fn();
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq({ method: 'GET' });
    const res = createRes();

    await handler(req, res);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(res.statusCode).toBe(405);
    expect(res.body).toEqual({ detail: 'Method not allowed' });
  });
});
