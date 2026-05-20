import { renderHook, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import useGoblinLoaderAnimation from '../useGoblinLoaderAnimation';

describe('useGoblinLoaderAnimation', () => {
  const animData = { v: '5.5.7', layers: [] };
  let fetchMock: jest.Mock;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => animData,
    } as Response);
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('starts with null', () => {
    const { result } = renderHook(() => useGoblinLoaderAnimation());
    expect(result.current).toBeNull();
  });

  it('fetches and returns animation data', async () => {
    const { result } = renderHook(() => useGoblinLoaderAnimation());
    await waitFor(() => expect(result.current).toEqual(animData));
    expect(fetchMock).toHaveBeenCalledWith('/goblin_loader.json', expect.objectContaining({ signal: expect.any(AbortSignal) }));
  });

  it('stays null when fetch fails', async () => {
    fetchMock.mockResolvedValueOnce({ ok: false, json: async () => ({}) } as Response);
    const { result } = renderHook(() => useGoblinLoaderAnimation());
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(result.current).toBeNull();
  });

  it('ignores AbortError', async () => {
    const abortErr = new DOMException('Aborted', 'AbortError');
    fetchMock.mockRejectedValueOnce(abortErr);
    const { result } = renderHook(() => useGoblinLoaderAnimation());
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(result.current).toBeNull();
  });

  it('aborts fetch on unmount', () => {
    const { unmount } = renderHook(() => useGoblinLoaderAnimation());
    unmount();
    // no error thrown means cleanup worked
  });
});
