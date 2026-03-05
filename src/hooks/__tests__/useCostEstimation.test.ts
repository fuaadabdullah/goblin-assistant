import { renderHook, act } from '@testing-library/react';
import { useCostEstimation } from '../useCostEstimation';

describe('useCostEstimation Hook', () => {
  it('should initialize with default values', () => {
    const { result } = renderHook(() => useCostEstimation());
    expect(result.current.estimatedCost).toBeDefined();
  });

  it('should calculate cost for input text', () => {
    const { result } = renderHook(() => useCostEstimation());

    act(() => {
      result.current.calculateForText?.('Hello world, this is a test message');
    });

    expect(result.current.estimatedCost).toBeGreaterThan(0);
  });

  it('should handle model changes', () => {
    const { result } = renderHook(() => useCostEstimation({ model: 'gpt-4' }));
    expect(result.current.estimatedCost).toBeDefined();
  });

  it('should reset cost estimate', () => {
    const { result } = renderHook(() => useCostEstimation());

    act(() => {
      result.current.calculateForText?.('Some text');
      result.current.reset?.();
    });

    expect(result.current.estimatedCost).toBe(0);
  });

  it('should handle provider changes', () => {
    const { result } = renderHook(() =>
      useCostEstimation({ provider: 'openai' }),
    );
    expect(result.current.estimatedCost).toBeDefined();
  });
});
