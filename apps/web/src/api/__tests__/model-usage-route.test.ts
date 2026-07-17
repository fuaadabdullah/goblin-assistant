import { afterEach, describe, expect, it, vi } from 'vitest';

import { GET } from '../../../app/api/debug/model-usage/route';

describe('/api/debug/model-usage route', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('forwards query params to the backend model-usage endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ rows: [], summary: { request_count: 0 } }), {
        status: 200,
      })
    );
    vi.stubGlobal('fetch', fetchMock);

    const response = await GET(
      new Request('http://localhost/api/debug/model-usage?provider=openai&model=gpt-4o')
    );

    const backendPath = ['/api', 'v1/debug/model-usage?provider=openai&model=gpt-4o'].join('/');
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(backendPath),
      expect.objectContaining({ method: 'GET' })
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      rows: [],
      summary: { request_count: 0 },
    });
  });
});
