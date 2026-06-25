import { afterEach, describe, expect, it, vi } from 'vitest';

import { GET } from '../../../app/api/system-status/route';

describe('/api/system-status route', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('maps top-level backend health components', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              status: 'warnings',
              components: {
                providers: { status: 'healthy' },
                routing: { status: 'healthy' },
              },
            }),
            { status: 200 }
          )
        )
        .mockResolvedValueOnce(new Response(JSON.stringify({ status: 'degraded' }), { status: 200 }))
    );

    const response = await GET();

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      models: 'ok',
      routing: 'ok',
      sandbox: 'degraded',
    });
  });
});
