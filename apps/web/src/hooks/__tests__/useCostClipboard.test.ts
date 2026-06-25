import { renderHook, act } from '@testing-library/react';
import { useCostClipboard } from '../useCostClipboard';

describe('useCostClipboard', () => {
  beforeEach(() => {
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
      configurable: true,
    });
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('initializes with no copy status', () => {
    const { result } = renderHook(() => useCostClipboard());
    expect(result.current.copyStatus).toBeNull();
  });

  it('copies a formatted summary using per-message precision', async () => {
    const { result } = renderHook(() => useCostClipboard());

    await act(async () => {
      await result.current.copyFormattedSummary({
        estimatedCost: 0.01234,
        estimatedTokens: 123,
        provider: 'openai',
        model: 'gpt-4o-mini',
        breakdown: [],
      });
    });

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      'Estimated cost: $0.0123\nEstimated tokens: 123'
    );
    expect(result.current.copyStatus).toBe('Copied');

    act(() => {
      vi.advanceTimersByTime(1500);
    });

    expect(result.current.copyStatus).toBeNull();
  });

  it('handles clipboard failures gracefully', async () => {
    (navigator.clipboard.writeText as vi.Mock).mockRejectedValueOnce(new Error('Clipboard error'));

    const { result } = renderHook(() => useCostClipboard());

    await act(async () => {
      await result.current.copyFormattedSummary({
        estimatedCost: 0.5,
        estimatedTokens: 7,
        provider: 'openai',
        model: 'gpt-4o-mini',
        breakdown: [],
      });
    });

    expect(result.current.copyStatus).toBe('Copy failed');
  });
});
