import { describe, expect, it, vi, afterEach } from 'vitest';

import { POST } from '../../../app/api/generate/route';

const makeRequest = () =>
  new Request('http://localhost/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: [{ role: 'user', content: 'Say hello' }],
    }),
  });

describe('/api/generate route', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('maps non-mock backend responses to frontend content', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            ok: true,
            result: { text: 'real answer' },
            provider: 'openai',
            model: 'gpt-4o-mini',
          }),
          { status: 200 }
        )
      )
    );
    vi.spyOn(console, 'warn').mockImplementation(() => {});

    const response = await POST(makeRequest());

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      content: 'real answer',
      model: 'gpt-4o-mini',
      provider: 'openai',
    });
  });

  it('returns 503 when the backend selects mock runtime', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            ok: true,
            result: { text: 'Mock response.' },
            provider: 'mock',
            model: 'mock-gpt',
          }),
          { status: 200 }
        )
      )
    );
    vi.spyOn(console, 'warn').mockImplementation(() => {});

    const response = await POST(makeRequest());

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toMatchObject({
      error: 'real-runtime-unavailable',
      reason: 'mock-provider-selected',
    });
  });

  it('returns 503 when backend providers are unavailable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ ok: false, error: 'no-configured-providers' }), {
          status: 200,
        })
      )
    );
    vi.spyOn(console, 'warn').mockImplementation(() => {});

    const response = await POST(makeRequest());

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toMatchObject({
      error: 'real-runtime-unavailable',
      reason: 'no-configured-providers',
    });
  });

  it('returns 503 on backend transport failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')));
    vi.spyOn(console, 'warn').mockImplementation(() => {});

    const response = await POST(makeRequest());

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toMatchObject({
      error: 'real-runtime-unavailable',
      reason: 'backend-transport-error',
    });
  });
});
