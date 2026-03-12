import { renderHook } from '@testing-library/react';
import { useCostEstimation } from '../useCostEstimation';

describe('useCostEstimation Hook', () => {
  it('should return null estimate for empty text', () => {
    const { result } = renderHook(() =>
      useCostEstimation({ orchestrationText: '', codeInput: '' }),
    );
    expect(result.current.estimate).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('should compute estimate for given text', () => {
    const { result } = renderHook(() =>
      useCostEstimation({
        orchestrationText: 'Hello world, this is a test message',
        codeInput: 'const x = 1;',
      }),
    );

    expect(result.current.estimate).not.toBeNull();
    expect(result.current.estimate!.estimatedCost).toBeGreaterThanOrEqual(0);
    expect(result.current.estimate!.estimatedTokens).toBeGreaterThan(0);
  });

  it('should include rate limit info', () => {
    const { result } = renderHook(() =>
      useCostEstimation({
        orchestrationText: 'Some text',
        codeInput: 'code',
      }),
    );

    expect(result.current.rateLimitInfo).toBeDefined();
  });

  it('should accept provider and model options', () => {
    const { result } = renderHook(() =>
      useCostEstimation({
        orchestrationText: 'text',
        codeInput: 'code',
        provider: 'openai',
        model: 'gpt-4',
      }),
    );

    expect(result.current.estimate).not.toBeNull();
    expect(result.current.estimate!.provider).toBe('openai');
    expect(result.current.estimate!.model).toBe('gpt-4');
  });

  it('should have no error by default', () => {
    const { result } = renderHook(() =>
      useCostEstimation({ orchestrationText: 'text', codeInput: '' }),
    );
    expect(result.current.error).toBeNull();
  });
});
