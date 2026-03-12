import { renderHook, act } from '@testing-library/react';
import { useProviderReorder } from '../useProviderReorder';

type ProviderConfig = { id: string; name: string; enabled: boolean; priority: number };

const makeProvider = (id: string): ProviderConfig => ({
  id,
  name: id,
  enabled: true,
  priority: 0,
});

describe('useProviderReorder', () => {
  const providerA = makeProvider('a');
  const providerB = makeProvider('b');
  const providerC = makeProvider('c');
  let onReorder: jest.Mock;

  beforeEach(() => {
    onReorder = jest.fn().mockResolvedValue(undefined);
  });

  it('returns initial state with no dragged provider', () => {
    const { result } = renderHook(() =>
      useProviderReorder({ providers: [providerA, providerB], onReorder })
    );
    expect(result.current.draggedProvider).toBeNull();
    expect(typeof result.current.handleDragStart).toBe('function');
    expect(typeof result.current.handleDragOver).toBe('function');
    expect(typeof result.current.handleDrop).toBe('function');
  });

  it('handleDragStart sets draggedProvider', () => {
    const { result } = renderHook(() =>
      useProviderReorder({ providers: [providerA, providerB], onReorder })
    );
    act(() => result.current.handleDragStart(providerA));
    expect(result.current.draggedProvider).toBe(providerA);
  });

  it('handleDragOver prevents default', () => {
    const { result } = renderHook(() =>
      useProviderReorder({ providers: [providerA, providerB], onReorder })
    );
    const e = { preventDefault: jest.fn() } as unknown as React.DragEvent<HTMLDivElement>;
    act(() => result.current.handleDragOver(e));
    expect(e.preventDefault).toHaveBeenCalled();
  });

  it('handleDrop does nothing if no provider is dragged', async () => {
    const { result } = renderHook(() =>
      useProviderReorder({ providers: [providerA, providerB], onReorder })
    );
    await act(async () => { await result.current.handleDrop(providerB); });
    expect(onReorder).not.toHaveBeenCalled();
  });

  it('handleDrop does nothing if dropped on same provider', async () => {
    const { result } = renderHook(() =>
      useProviderReorder({ providers: [providerA, providerB], onReorder })
    );
    act(() => result.current.handleDragStart(providerA));
    await act(async () => { await result.current.handleDrop(providerA); });
    expect(onReorder).not.toHaveBeenCalled();
  });

  it('handleDrop reorders and calls onReorder', async () => {
    const { result } = renderHook(() =>
      useProviderReorder({ providers: [providerA, providerB, providerC], onReorder })
    );
    act(() => result.current.handleDragStart(providerA));
    await act(async () => { await result.current.handleDrop(providerC); });
    expect(onReorder).toHaveBeenCalledWith([providerB, providerC, providerA]);
    expect(result.current.draggedProvider).toBeNull();
  });

  it('clears draggedProvider even if onReorder throws', async () => {
    onReorder.mockRejectedValue(new Error('fail'));
    const { result } = renderHook(() =>
      useProviderReorder({ providers: [providerA, providerB], onReorder })
    );
    act(() => result.current.handleDragStart(providerA));
    await act(async () => {
      try { await result.current.handleDrop(providerB); } catch { /* expected */ }
    });
    expect(result.current.draggedProvider).toBeNull();
  });

  it('handleDrop does nothing if dragged provider not found in list', async () => {
    const orphan = makeProvider('orphan');
    const { result } = renderHook(() =>
      useProviderReorder({ providers: [providerA, providerB], onReorder })
    );
    act(() => result.current.handleDragStart(orphan));
    await act(async () => { await result.current.handleDrop(providerA); });
    expect(onReorder).not.toHaveBeenCalled();
  });

  it('handleDrop does nothing if target provider not found in list', async () => {
    const orphan = makeProvider('orphan');
    const { result } = renderHook(() =>
      useProviderReorder({ providers: [providerA, providerB], onReorder })
    );
    act(() => result.current.handleDragStart(providerA));
    await act(async () => { await result.current.handleDrop(orphan); });
    expect(onReorder).not.toHaveBeenCalled();
  });
});
