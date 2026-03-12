import { UiError, toUiError } from '../ui-error';

describe('UI Error Utilities', () => {
  describe('UiError class', () => {
    it('should create UiError with code and userMessage', () => {
      const error = new UiError({ code: 'ERR_TEST', userMessage: 'Something went wrong' });

      expect(error.message).toBe('Something went wrong');
      expect(error.code).toBe('ERR_TEST');
      expect(error.userMessage).toBe('Something went wrong');
      expect(error instanceof Error).toBe(true);
    });

    it('should accept an optional cause', () => {
      const cause = new Error('original');
      const error = new UiError({ code: 'ERR_WRAP', userMessage: 'Wrapped error' }, cause);

      expect(error.cause).toBe(cause);
      expect(error.code).toBe('ERR_WRAP');
    });
  });

  describe('toUiError', () => {
    it('should return existing UiError as-is', () => {
      const original = new UiError({ code: 'ERR', userMessage: 'test' });
      const result = toUiError(original, { code: 'FALLBACK', userMessage: 'fallback' });

      expect(result).toBe(original);
    });

    it('should wrap standard Error with fallback payload', () => {
      const standardError = new Error('Standard error message');
      const fallback = { code: 'ERR_FALLBACK', userMessage: 'Fallback message' };

      const uiError = toUiError(standardError, fallback);

      expect(uiError instanceof UiError).toBe(true);
      expect(uiError.code).toBe('ERR_FALLBACK');
      expect(uiError.userMessage).toBe('Fallback message');
      expect(uiError.cause).toBe(standardError);
    });

    it('should handle unknown error types with fallback', () => {
      const fallback = { code: 'ERR_UNKNOWN', userMessage: 'An error occurred' };

      const uiError = toUiError('string error', fallback);

      expect(uiError instanceof UiError).toBe(true);
      expect(uiError.code).toBe('ERR_UNKNOWN');
    });

    it('should handle null/undefined errors with fallback', () => {
      const fallback = { code: 'ERR_NULL', userMessage: 'Something went wrong' };

      const uiError1 = toUiError(null, fallback);
      const uiError2 = toUiError(undefined, fallback);

      expect(uiError1.code).toBe('ERR_NULL');
      expect(uiError2.code).toBe('ERR_NULL');
    });
  });
});
