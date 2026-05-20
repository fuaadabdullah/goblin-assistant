import { renderHook, act } from '@testing-library/react';
import { useCostStreaming } from '../useCostStreaming';

describe('useCostStreaming Hook', () => {
  it('should initialize with empty state', () => {
    const { result } = renderHook(() => useCostStreaming({ estimate: null }));

    expect(result.current.streamLines).toEqual([]);
    expect(result.current.streaming).toBe(false);
  });

  it('should show summary when estimate is provided', () => {
    const estimate = { estimatedCost: 0.01, estimatedTokens: 100 };
    const { result } = renderHook(() => useCostStreaming({ estimate }));

    expect(result.current.showSummary).toBe(true);
  });

  it('should start streaming with parameters', () => {
    const { result } = renderHook(() => useCostStreaming({ estimate: null }));

    act(() => {
      result.current.startStreaming('instruction text', 'code input', 'openai', 'gpt-4');
    });

    expect(result.current.streaming).toBe(true);
    expect(result.current.streamLines.length).toBeGreaterThan(0);
    expect(result.current.streamLines).toEqual(
      expect.arrayContaining([expect.stringContaining('openai')]),
    );
  });

  it('should reset streaming state', () => {
    const { result } = renderHook(() => useCostStreaming({ estimate: null }));

    act(() => {
      result.current.startStreaming('text', 'code');
    });

    act(() => {
      result.current.resetStreaming();
    });

    expect(result.current.streaming).toBe(false);
    expect(result.current.streamLines).toEqual([]);
  });
});
