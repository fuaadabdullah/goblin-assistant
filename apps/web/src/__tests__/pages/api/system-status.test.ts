import { afterEach, describe, expect, it, vi } from 'vitest';

import { GET } from '../../../../app/api/system-status/route';

describe('/api/system-status', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('maps model status from provider health instead of top-level app status', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              status: 'warnings',
              components: {
                providers: { status: 'degraded' },
                routing: { status: 'healthy' },
              },
            }),
            { status: 200 }
          )
        )
        .mockResolvedValueOnce(new Response(JSON.stringify({ status: 'healthy' }), { status: 200 }))
    );

    const response = await GET();

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      models: 'degraded',
      routing: 'ok',
      sandbox: 'ok',
    });
  });

  it('returns unknown statuses when backend health is unavailable', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 503 }))
        .mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 503 }))
    );

    const response = await GET();

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      models: 'unknown',
      routing: 'unknown',
      sandbox: 'unknown',
    });
  });
});
