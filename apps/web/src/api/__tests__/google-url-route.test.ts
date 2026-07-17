import { afterEach, describe, expect, it, vi } from 'vitest';

import { GET } from '../../../app/api/auth/google/url/route';

describe('/api/auth/google/url route', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('forwards the GET to the backend and returns the authorization URL', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ authorization_url: 'https://accounts.google.com/o/oauth2/v2/auth?state=xyz' }), {
          status: 200,
          headers: { 'x-correlation-id': 'cid-456' },
        })
      )
    );

    const response = await GET();

    expect(response.status).toBe(200);
    expect(response.headers.get('X-Correlation-ID')).toBe('cid-456');
    const body = await response.json();
    expect(body.authorization_url).toBe('https://accounts.google.com/o/oauth2/v2/auth?state=xyz');
  });

  it('returns 502 when the backend is unreachable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('Connection refused'))
    );

    const response = await GET();

    expect(response.status).toBe(502);
    const body = await response.json();
    expect(body.detail).toBe('Backend unreachable');
  });
});