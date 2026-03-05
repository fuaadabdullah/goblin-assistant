import { renderHook, act } from '@testing-library/react';
import { useCostClipboard } from '../useCostClipboard';

describe('useCostClipboard Hook', () => {
  beforeEach(() => {
    // Mock clipboard API
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: jest.fn(),
      },
      configurable: true,
    });
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useCostClipboard());
    expect(result.current.isCopied).toBe(false);
  });

  it('should copy cost to clipboard', async () => {
    const { result } = renderHook(() => useCostClipboard());

    act(() => {
      result.current.copyCost?.('$0.15');
    });

    // Should set isCopied to true
    expect(result.current.isCopied).toBe(true);
  });

  it('should handle copy error gracefully', async () => {
    const { result } = renderHook(() => useCostClipboard());

    // Mock clipboard error
    (navigator.clipboard.writeText as jest.Mock).mockRejectedValueOnce(
      new Error('Clipboard error'),
    );

    act(() => {
      result.current.copyCost?.('$0.15');
    });

    // Should handle error without crashing
  });

  it('should reset copy state after delay', async () => {
    jest.useFakeTimers();
    const { result } = renderHook(() => useCostClipboard());

    act(() => {
      result.current.copyCost?.('$0.15');
    });

    expect(result.current.isCopied).toBe(true);

    act(() => {
      jest.advanceTimersByTime(2000);
    });

    jest.useRealTimers();
    // Should reset after timeout
  });
});
