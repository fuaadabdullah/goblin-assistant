import { UiError, toUiError } from '../ui-error';

describe('UI Error Utilities', () => {
  describe('UiError class', () => {
    it('should create UiError with message and payload', () => {
      const payload = { title: 'Error', message: 'Something went wrong' };
      const error = new UiError('UI error occurred', payload);

      expect(error.message).toBe('UI error occurred');
      expect(error.payload).toEqual(payload);
      expect(error instanceof Error).toBe(true);
    });

    it('should handle UiError with title only', () => {
      const payload = { title: 'Error' };
      const error = new UiError('UI error', payload);

      expect(error.payload.title).toBe('Error');
    });
  });

  describe('toUiError', () => {
    it('should convert Error to UiError', () => {
      const standardError = new Error('Standard error message');
      const fallback = { title: 'Fallback Title', message: 'Fallback message' };

      const uiError = toUiError(standardError, fallback);

      expect(uiError instanceof UiError).toBe(true);
      expect(uiError.payload).toBeDefined();
    });

    it('should handle unknown error types', () => {
      const unknownError = 'string error';
      const fallback = { title: 'Error', message: 'An error occurred' };

      const uiError = toUiError(unknownError, fallback);

      expect(uiError instanceof UiError).toBe(true);
      expect(uiError.payload).toEqual(fallback);
    });

    it('should handle null/undefined errors with fallback', () => {
      const fallback = { title: 'Error', message: 'Something went wrong' };

      const uiError1 = toUiError(null, fallback);
      const uiError2 = toUiError(undefined, fallback);

      expect(uiError1.payload).toEqual(fallback);
      expect(uiError2.payload).toEqual(fallback);
    });

    it('should preserve error details when available', () => {
      const error = new Error('Detailed error message');
      const fallback = { title: 'Fallback', message: 'Fallback message' };

      const uiError = toUiError(error, fallback);

      expect(uiError.message).toContain('Detailed error message');
    });
  });
});
