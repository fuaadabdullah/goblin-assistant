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

describe('proxy streaming lifecycle', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('delivers the first chunk before upstream completion and cancels upstream', async () => {
    const cancel = vi.fn();
    const upstream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('data: first\n\n'));
      },
      cancel,
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(upstream, {
        headers: { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' },
      })
    );
    vi.stubGlobal('fetch', fetchMock);
    const response = await POST(
      new Request('http://localhost/api/chat/stream', { method: 'POST' }),
      {
        params: Promise.resolve({ path: ['chat', 'stream'] }),
      }
    );
    const reader = response.body!.getReader();
    const first = await reader.read();
    expect(new TextDecoder().decode(first.value)).toBe('data: first\n\n');
    expect(response.headers.get('cache-control')).toBe('no-cache');
    await reader.cancel();
    expect(cancel).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0]![1].signal.aborted).toBe(true);
  });

  it('times out a body that stalls after headers', async () => {
    vi.useFakeTimers();
    const cancel = vi.fn();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(new ReadableStream({ cancel }))));
    const response = await GET(new Request('http://localhost/api/metrics'), {
      params: Promise.resolve({ path: ['metrics'] }),
    });
    const read = response.body!.getReader().read();
    const failure = expect(read).rejects.toThrow('timed out');
    await vi.advanceTimersByTimeAsync(10001);
    await failure;
    expect(cancel).toHaveBeenCalledOnce();
  });

  it('propagates a client abort while streaming', async () => {
    const client = new AbortController();
    const cancel = vi.fn();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(new ReadableStream({ cancel }))));
    const request = new Request('http://localhost/api/metrics');
    Object.defineProperty(request, 'signal', { value: client.signal });
    const response = await GET(request, {
      params: Promise.resolve({ path: ['metrics'] }),
    });
    const read = response.body!.getReader().read();
    const failure = expect(read).rejects.toThrow('client left');
    client.abort(new Error('client left'));
    await failure;
    expect(cancel).toHaveBeenCalledOnce();
  });

  it('preserves an empty 204 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    const response = await POST(
      new Request('http://localhost/api/auth/logout', { method: 'POST' }),
      {
        params: Promise.resolve({ path: ['auth', 'logout'] }),
      }
    );
    expect(response.status).toBe(204);
    expect(response.body).toBeNull();
  });
});
