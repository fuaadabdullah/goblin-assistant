import { afterEach, describe, expect, it, vi } from 'vitest';

import { POST } from '../../../app/api/auth/validate/route';

describe('/api/auth/validate route', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('forwards the bearer token in the backend validation body', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ success: true, data: { valid: true } }), { status: 200 })
      );
    vi.stubGlobal('fetch', fetchMock);

    const response = await POST(
      new Request('http://localhost/api/auth/validate', {
        method: 'POST',
        headers: { Authorization: 'Bearer session-token' },
        body: JSON.stringify({}),
      })
    );

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/validate'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ token: 'session-token' }),
      })
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      success: true,
      data: { valid: true },
    });
  });
});
