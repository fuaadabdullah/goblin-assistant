import { UiError, toUiError } from '../ui-error';

describe('UiError', () => {
  it('creates an error with code and user message', () => {
    const error = new UiError({ code: 'NOT_FOUND', userMessage: 'Item not found' });
    expect(error.code).toBe('NOT_FOUND');
    expect(error.userMessage).toBe('Item not found');
    expect(error.message).toBe('Item not found');
  });

  it('extends Error class', () => {
    const error = new UiError({ code: 'ERR', userMessage: 'Error!' });
    expect(error).toBeInstanceOf(Error);
  });

  it('stores cause when provided', () => {
    const cause = new Error('Original cause');
    const error = new UiError({ code: 'CAUSED', userMessage: 'Caused error' }, cause);
    expect(error.cause).toBe(cause);
  });
});

describe('toUiError', () => {
  it('returns same UiError instance when input is UiError', () => {
    const original = new UiError({ code: 'TEST', userMessage: 'Test' });
    const result = toUiError(original, { code: 'FALLBACK', userMessage: 'Fallback' });
    expect(result).toBe(original);
    expect(result.code).toBe('TEST');
  });

  it('wraps non-UiError in UiError with fallback', () => {
    const raw = new Error('Something broke');
    const result = toUiError(raw, { code: 'UNKNOWN', userMessage: 'Something went wrong' });
    expect(result).toBeInstanceOf(UiError);
    expect(result.code).toBe('UNKNOWN');
    expect(result.userMessage).toBe('Something went wrong');
    expect(result.cause).toBe(raw);
  });

  it('wraps string error in UiError', () => {
    const result = toUiError('string error', { code: 'STRING', userMessage: 'String error' });
    expect(result.code).toBe('STRING');
    expect(result.cause).toBe('string error');
  });
});
