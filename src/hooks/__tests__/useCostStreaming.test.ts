import { renderHook, act } from '@testing-library/react';
import { useCostStreaming } from '../useCostStreaming';

describe('useCostStreaming Hook', () => {
  it('should initialize with provided estimate', () => {
    const estimate = { inputTokens: 100, outputTokens: 50, totalCost: 0.01 };
    const { result } = renderHook(() => useCostStreaming({ estimate }));

    expect(result.current.currentCost).toBeDefined();
  });

  it('should update cost on new data', () => {
    const estimate = { inputTokens: 100, outputTokens: 50, totalCost: 0.01 };
    const { result } = renderHook(() => useCostStreaming({ estimate }));

    act(() => {
      result.current.onDataChunk?.({
        tokens: 10,
        cost: 0.002,
      });
    });

    expect(result.current.currentCost).toBeGreaterThanOrEqual(
      estimate.totalCost,
    );
  });

  it('should handle streaming completion', () => {
    const estimate = { inputTokens: 100, outputTokens: 50, totalCost: 0.01 };
    const { result } = renderHook(() => useCostStreaming({ estimate }));

    act(() => {
      result.current.onComplete?.();
    });

    // Should finalize cost
  });

  it('should reset streaming state', () => {
    const estimate = { inputTokens: 100, outputTokens: 50, totalCost: 0.01 };
    const { result } = renderHook(() => useCostStreaming({ estimate }));

    act(() => {
      result.current.onDataChunk?.({ tokens: 10, cost: 0.002 });
      result.current.reset?.();
    });

    expect(result.current.currentCost).toBe(estimate.totalCost);
  });
});
