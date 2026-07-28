import { afterEach, describe, expect, it, vi } from 'vitest';

import { POST } from '../../../app/api/auth/google/callback/route';

describe('/api/auth/google/callback route', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('forwards the callback payload to the backend and preserves correlation id', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ token: 'jwt-token' }), {
          status: 200,
          headers: { 'x-correlation-id': 'cid-123' },
        })
      )
    );

    const response = await POST(
      new Request('http://localhost/api/auth/google/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: 'abc', state: 'xyz' }),
      })
    );

    expect(response.status).toBe(200);
    expect(response.headers.get('X-Correlation-ID')).toBe('cid-123');
    await expect(response.json()).resolves.toEqual({ token: 'jwt-token' });
  });
});
