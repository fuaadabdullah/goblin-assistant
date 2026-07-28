type MockReq = {
  method: string;
};

type MockRes = {
  statusCode: number;
  body: unknown;
  status: (code: number) => MockRes;
  json: (payload: unknown) => MockRes;
  end: () => MockRes;
};

function createReq(overrides: Partial<MockReq> = {}): MockReq {
  return {
    method: 'GET',
    ...overrides,
  };
}

function createRes(): MockRes {
  return {
    statusCode: 200,
    body: null,
    status(code: number) {
      this.statusCode = code;
      return this;
    },
    json(payload: unknown) {
      this.body = payload;
      return this;
    },
    end() {
      return this;
    },
  };
}

function createFetchResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response;
}

function loadHandler() {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  return require('../../../pages/api/system-status').default as (
    req: MockReq,
    res: MockRes
  ) => Promise<void>;
}

describe('/api/system-status', () => {
  const originalFetch = global.fetch;
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv, GOBLIN_BACKEND_URL: 'https://backend.example' };
  });

  afterEach(() => {
    process.env = originalEnv;
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('maps model status from provider health instead of top-level app status', async () => {
    const fetchMock = jest.fn().mockResolvedValue(
      createFetchResponse(200, {
        status: 'warnings',
        components: {
          providers: { status: 'degraded' },
          routing: { status: 'healthy' },
        },
      })
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq();
    const res = createRes();

    await handler(req, res);

    expect(fetchMock.mock.calls[0][0]).toBe('https://backend.example/health');
    expect(res.statusCode).toBe(200);
    expect(res.body).toMatchObject({
      models: 'degraded',
      routing: 'ok',
      sandbox: 'unknown',
    });
  });

  it('returns unknown statuses when backend health is unavailable', async () => {
    const fetchMock = jest.fn().mockResolvedValue(createFetchResponse(503, {}));
    global.fetch = fetchMock as unknown as typeof fetch;

    const handler = loadHandler();
    const req = createReq();
    const res = createRes();

    await handler(req, res);

    expect(res.statusCode).toBe(200);
    expect(res.body).toEqual({
      models: 'unknown',
      routing: 'unknown',
      sandbox: 'unknown',
    });
  });
});
