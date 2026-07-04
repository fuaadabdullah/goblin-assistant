import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSystemStatus } from '../useSystemStatus';

describe('useSystemStatus', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('fetches once on mount and stays stable across rerenders', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        models: 'ok',
        routing: 'ok',
        sandbox: 'ok',
      }),
    } as Response);

    const { result, rerender } = renderHook(() => useSystemStatus({ pollIntervalMs: 60_000 }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.status.models).toBe('ok');
    expect(result.current.status.routing).toBe('ok');
    expect(result.current.status.sandbox).toBe('ok');
    expect(fetchMock).toHaveBeenCalledTimes(1);

    rerender();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
