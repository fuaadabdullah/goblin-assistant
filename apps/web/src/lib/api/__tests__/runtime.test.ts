import { apiClient } from '../index';

vi.mock('../shared', async () => {
  const actual = await vi.importActual('../shared');
  return {
    ...actual,
    getFrontend: vi.fn(),
    postFrontend: vi.fn(),
  };
});

import { getFrontend, postFrontend } from '../shared';

const mockGetFrontend = getFrontend as vi.MockedFunction<typeof getFrontend>;
const mockPostFrontend = postFrontend as vi.MockedFunction<typeof postFrontend>;

beforeEach(() => {
  vi.clearAllMocks();
});

describe('apiClient runtime methods', () => {
  it('getGoblins calls /api/goblins', async () => {
    mockGetFrontend.mockResolvedValue({
      items: [{ id: 'g1', name: 'g1', title: 'G1', status: 'active', active: true }],
      total: 1,
      limit: 100,
      order: 'catalog_order',
    });
    const result = await apiClient.getGoblins();
    expect(result).toHaveLength(1);
    expect(mockGetFrontend).toHaveBeenCalledWith('/api/runtime/goblins');
  });

  it('getHistory calls /api/history/{goblin} with capped limit', async () => {
    mockGetFrontend.mockResolvedValue({
      items: [],
      total: 0,
      limit: 100,
      next_cursor: null,
      order: 'newest_first',
    });
    await apiClient.getHistory('docs-writer', 9999);
    expect(mockGetFrontend).toHaveBeenCalledWith('/api/runtime/history/docs-writer?limit=100');
  });

  it('getStats calls /api/stats/{goblin}', async () => {
    mockGetFrontend.mockResolvedValue({
      goblin_id: 'demo',
      window: {
        hours: 24,
        started_at: '2026-08-02T00:00:00Z',
        ended_at: '2026-08-03T00:00:00Z',
      },
      counters: {
        total_tasks: 7,
        completed_tasks: 7,
        failed_tasks: 0,
      },
      latency: {
        average_duration_ms: null,
        p95_duration_ms: null,
      },
      success_rate: 1,
      total_cost: null,
    });
    const stats = await apiClient.getStats('demo');
    expect(stats.counters.total_tasks).toBe(7);
    expect(mockGetFrontend).toHaveBeenCalledWith('/api/runtime/stats/demo');
  });

  it('parseOrchestration posts /api/orchestrate/parse', async () => {
    mockPostFrontend.mockResolvedValue({ steps: [], total_batches: 0, max_parallel: 0 });
    await apiClient.parseOrchestration('a THEN b', 'demo');
    expect(mockPostFrontend).toHaveBeenCalledWith('/api/runtime/orchestrate/parse', {
      text: 'a THEN b',
      default_goblin: 'demo',
    });
  });
});
