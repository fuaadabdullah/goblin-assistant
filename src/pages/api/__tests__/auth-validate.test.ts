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
  return require('../auth/validate').default as (
    req: MockReq,
    res: MockRes,
  ) => Promise<void>;
}

describe('/api/auth/validate thin proxy', () => {
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

  it('forwards authorization and internal key to backend /v1/auth/validate', async () => {
    process.env.GOBLIN_BACKEND_URL = 'https://backend.example';
    process.env.INTERNAL_PROXY_API_KEY = 'proxy-key';

    const fetchMock = jest.fn().mockResolvedValue(
      createFetchResponse({
        status: 200,
        body: { valid: true, user: { id: 'u1', email: 'u1@example.com' } },
        headers: { 'x-correlation-id': 'cid-auth' },
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq({
      headers: { authorization: 'Bearer token-123' },
      body: { foo: 'bar' },
    });
    const res = createRes();

    await handler(req, res);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe('https://backend.example/v1/auth/validate');

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe('POST');
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer token-123');
    expect((init.headers as Record<string, string>)['X-Internal-API-Key']).toBe('proxy-key');
    expect(JSON.parse(String(init.body))).toEqual({ foo: 'bar' });

    expect(res.statusCode).toBe(200);
    expect(res.headers['x-correlation-id']).toBe('cid-auth');
    expect(res.body).toEqual({ valid: true, user: { id: 'u1', email: 'u1@example.com' } });
  });

  it('maps transport errors to 502', async () => {
    process.env.GOBLIN_BACKEND_URL = 'https://backend.example';

    const fetchMock = jest.fn().mockRejectedValue(new Error('connect timeout'));
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq();
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
