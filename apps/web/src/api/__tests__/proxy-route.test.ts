import { afterEach, describe, expect, it, vi } from 'vitest';

import { GET, POST } from '../../../app/api/[...path]/route';

describe('/api/[...path] route', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('forwards auth prefix requests to the backend auth namespace', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ access_token: 'jwt-token' }), { status: 200 })
      );
    vi.stubGlobal('fetch', fetchMock);

    const response = await POST(
      new Request('http://localhost/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'test@example.com', password: 'secret' }),
      }),
      {
        params: Promise.resolve({ path: ['auth', 'login'] }),
      }
    );

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/login'),
      expect.objectContaining({ method: 'POST' })
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ access_token: 'jwt-token' });
  });

  it('forwards costs prefix requests to the routing costs backend namespace', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ total_cost: 123.45 }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const response = await GET(new Request('http://localhost/api/costs/summary'), {
      params: Promise.resolve({ path: ['costs', 'summary'] }),
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/routing/costs/summary'),
      expect.objectContaining({ method: 'GET' })
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ total_cost: 123.45 });
  });

  it('forwards metrics requests to the raw Prometheus endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('# HELP foo_total Count\nfoo_total 1\n', {
        status: 200,
        headers: {
          'content-type': 'text/plain; version=0.0.4',
          'x-correlation-id': 'cid-metrics',
        },
      })
    );
    vi.stubGlobal('fetch', fetchMock);

    const response = await GET(new Request('http://localhost/api/metrics'), {
      params: Promise.resolve({ path: ['metrics'] }),
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/metrics'),
      expect.objectContaining({ method: 'GET' })
    );
    expect(response.status).toBe(200);
    expect(response.headers.get('Content-Type')).toContain('text/plain');
    expect(response.headers.get('X-Correlation-ID')).toBe('cid-metrics');
    await expect(response.text()).resolves.toContain('foo_total 1');
  });

  it('returns 404 for unknown proxy paths', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const response = await GET(new Request('http://localhost/api/unknown'), {
      params: Promise.resolve({ path: ['unknown'] }),
    });

    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toEqual({ detail: 'Not found' });
  });
});
