import { apiClient } from '../index';

vi.mock('../shared', async () => {
  const actual = await vi.importActual('../shared');
  return {
    ...actual,
    getBackend: vi.fn(),
    postBackend: vi.fn(),
  };
});

import { getBackend, postBackend } from '../shared';

const mockGetBackend = getBackend as vi.MockedFunction<typeof getBackend>;
const mockPostBackend = postBackend as vi.MockedFunction<typeof postBackend>;

beforeEach(() => {
  vi.clearAllMocks();
});

describe('apiClient runtime methods', () => {
  it('getGoblins calls /api/goblins', async () => {
    mockGetBackend.mockResolvedValue([{ id: 'g1', name: 'g1', title: 'G1', status: 'available' }]);
    const result = await apiClient.getGoblins();
    expect(result).toHaveLength(1);
    expect(mockGetBackend).toHaveBeenCalledWith('/api/v1/api/goblins');
  });

  it('getHistory calls /api/history/{goblin} with capped limit', async () => {
    mockGetBackend.mockResolvedValue([]);
    await apiClient.getHistory('docs-writer', 9999);
    expect(mockGetBackend).toHaveBeenCalledWith('/api/v1/api/history/docs-writer?limit=100');
  });

  it('getStats calls /api/stats/{goblin}', async () => {
    mockGetBackend.mockResolvedValue({ total_tasks: 7 });
    const stats = await apiClient.getStats('demo');
    expect(stats.total_tasks).toBe(7);
    expect(mockGetBackend).toHaveBeenCalledWith('/api/v1/api/stats/demo');
  });

  it('parseOrchestration posts /api/orchestrate/parse', async () => {
    mockPostBackend.mockResolvedValue({ steps: [], total_batches: 0, max_parallel: 0 });
    await apiClient.parseOrchestration('a THEN b', 'demo');
    expect(mockPostBackend).toHaveBeenCalledWith('/api/v1/api/orchestrate/parse', {
      text: 'a THEN b',
      default_goblin: 'demo',
    });
  });
});
