import { afterEach, describe, expect, it, vi } from 'vitest';

describe('GET /api/health', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
  });

  it('returns a degraded proxy response when the backend payload is malformed', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue({ services: [] }),
      })
    );

    const { GET } = await import('../../../../../app/api/health/route');
    const response = await GET();
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toMatchObject({
      overall: 'degraded',
      proxy: { status: 'backend_unavailable', reason: 'backend_status_200' },
    });
  });
});