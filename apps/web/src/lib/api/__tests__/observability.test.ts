import { apiClient } from '../index';

vi.mock('../shared', async () => {
  const actual = await vi.importActual('../shared');
  return {
    ...actual,
    getFrontend: vi.fn(),
    frontendHttp: {
      get: vi.fn(),
    },
  };
});

import { frontendHttp, getFrontend } from '../shared';

const mockGetFrontend = getFrontend as vi.MockedFunction<typeof getFrontend>;
const mockFrontendHttpGet = vi.mocked(frontendHttp.get);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('apiClient observability methods', () => {
  it('getModelUsage calls the internal debug model-usage path', async () => {
    mockGetFrontend.mockResolvedValue({ rows: [], summary: { request_count: 0 } } as any);

    await apiClient.getModelUsage('openai', 'gpt-4o');

    expect(mockGetFrontend).toHaveBeenCalledWith(
      '/api/debug/model-usage?provider=openai&model=gpt-4o'
    );
  });

  it('getPrometheusMetrics calls the internal metrics route as plaintext', async () => {
    mockFrontendHttpGet.mockResolvedValue({ data: '# HELP foo\nfoo 1\n' } as any);

    const metrics = await apiClient.getPrometheusMetrics();

    expect(metrics).toContain('foo 1');
    expect(mockFrontendHttpGet).toHaveBeenCalledWith('/api/metrics', {
      responseType: 'text',
      transformResponse: [expect.any(Function)],
    });
  });
});
