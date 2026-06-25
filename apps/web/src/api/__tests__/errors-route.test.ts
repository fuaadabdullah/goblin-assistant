import { describe, expect, it, vi } from 'vitest';

import { POST } from '../../../app/api/errors/route';

describe('/api/errors route', () => {
  it('accepts error reports and returns an acknowledgement', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const response = await POST(
      new Request('http://localhost/api/errors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: 'boom',
          timestamp: '2026-06-20T00:00:00.000Z',
          userAgent: 'test-agent',
          url: 'http://localhost',
        }),
      })
    );

    expect(response.status).toBe(202);
    await expect(response.json()).resolves.toEqual({ ok: true });
    expect(warnSpy).toHaveBeenCalledOnce();

    warnSpy.mockRestore();
  });
});
