import { prefetchCsrfToken, getCsrfToken } from '../csrf';
import { getBackend } from '../http-helpers';

vi.mock('../http-helpers', () => ({
  getBackend: vi.fn(),
  extractApiErrorMessage: (payload: unknown, fallback = 'Request failed') => {
    if (!payload || typeof payload !== 'object') return fallback;
    const data = payload as Record<string, unknown>;
    if (typeof data['detail'] === 'string' && data['detail'].trim()) return data['detail'];
    if (typeof data['message'] === 'string' && data['message'].trim()) return data['message'];
    return fallback;
  },
}));

describe('CSRF Token Management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('prefetch fetches CSRF token from backend', async () => {
    const mockToken = 'test-csrf-token-123';
    vi.mocked(getBackend).mockResolvedValue({ csrf_token: mockToken });

    prefetchCsrfToken();
    const token = await getCsrfToken();

    expect(token).toBe(mockToken);
    expect(vi.mocked(getBackend)).toHaveBeenCalledWith(
      expect.stringContaining('/auth/csrf-token'),
      expect.any(Object)
    );
  });

  it('deduplicates concurrent prefetch calls', async () => {
    const mockToken = 'dedup-token-456';
    vi.mocked(getBackend).mockResolvedValue({ csrf_token: mockToken });

    // Start multiple prefetches
    prefetchCsrfToken();
    prefetchCsrfToken();
    prefetchCsrfToken();

    // All should resolve to the same token
    const token1 = await getCsrfToken();
    expect(token1).toBe(mockToken);

    // Backend should only be called once
    expect(vi.mocked(getBackend)).toHaveBeenCalledTimes(1);
  });

  it('consumes token after first use', async () => {
    const mockToken = 'single-use-token-789';
    vi.mocked(getBackend).mockResolvedValue({ csrf_token: mockToken });

    prefetchCsrfToken();
    const token1 = await getCsrfToken();
    expect(token1).toBe(mockToken);

    // Second call should fetch again since token was consumed
    vi.mocked(getBackend).mockResolvedValue({ csrf_token: 'new-token' });
    const token2 = await getCsrfToken();
    expect(token2).toBe('new-token');
    expect(vi.mocked(getBackend)).toHaveBeenCalledTimes(2);
  });

  it('handles backend errors gracefully', async () => {
    vi.mocked(getBackend).mockRejectedValue(new Error('Network error'));

    prefetchCsrfToken();

    await expect(getCsrfToken()).rejects.toThrow('Network error');
    expect(vi.mocked(getBackend)).toHaveBeenCalled();
  });

  it('preserves backend details when csrf token payload is missing', async () => {
    vi.mocked(getBackend).mockResolvedValueOnce({ detail: 'Auth service warming up' });

    await expect(getCsrfToken()).rejects.toThrow('Auth service warming up');
  });

  it('retries after prefetch failure', async () => {
    // First prefetch fails
    vi.mocked(getBackend).mockRejectedValueOnce(new Error('Network error'));

    prefetchCsrfToken();
    await expect(getCsrfToken()).rejects.toThrow();

    // Second attempt should retry the fetch
    const mockToken = 'retry-token';
    vi.mocked(getBackend).mockResolvedValueOnce({ csrf_token: mockToken });

    const token = await getCsrfToken();
    expect(token).toBe(mockToken);
    expect(vi.mocked(getBackend)).toHaveBeenCalledTimes(2);
  });
});
