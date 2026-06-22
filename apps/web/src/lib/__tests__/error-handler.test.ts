import { describe, expect, it } from 'vitest';
import { handleError, isRetryable } from '../error/handler';

describe('error handler', () => {
  it('preserves server messages for retryable HTTP errors', () => {
    const error = {
      status: 503,
      response: {
        status: 503,
        data: {
          error: {
            message: 'Provider temporarily unavailable',
          },
        },
      },
    };

    const handled = handleError(error);

    expect(handled.code).toBe('HTTP_503');
    expect(handled.userMessage).toBe('Provider temporarily unavailable');
    expect(handled.retryable).toBe(true);
    expect(isRetryable(error)).toBe(true);
  });

  it('keeps the fallback for retryable HTTP errors without details', () => {
    const handled = handleError({ status: 502, response: { status: 502, data: {} } });

    expect(handled.code).toBe('HTTP_502');
    expect(handled.userMessage).toBe('A server error occurred. Please try again in a moment.');
  });

  it('preserves normalized responseData details for retryable HTTP errors', () => {
    const error = Object.assign(new Error('Request failed'), {
      status: 503,
      responseData: {
        error: 'real-runtime-unavailable',
        detail: 'Real model runtime is unavailable. Please try again later.',
        reason: 'mock-provider-selected',
      },
    });

    const handled = handleError(error);

    expect(handled.code).toBe('HTTP_503');
    expect(handled.userMessage).toBe(
      'Real model runtime is unavailable. Please try again later.'
    );
  });
});
