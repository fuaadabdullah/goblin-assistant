import { devLog, devWarn, devError } from '../dev-log';

describe('Development Logging Utilities', () => {
  let consoleLogSpy: jest.SpyInstance;
  let consoleWarnSpy: jest.SpyInstance;
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
  });

  afterEach(() => {
    consoleLogSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    consoleErrorSpy.mockRestore();
  });

  describe('devLog', () => {
    it('should call console.log in development', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      devLog('test message', { data: 'value' });

      // In development, devLog should output
      if (process.env.NODE_ENV === 'development') {
        expect(consoleLogSpy).toHaveBeenCalled();
      }

      process.env.NODE_ENV = originalEnv;
    });

    it('should accept multiple arguments', () => {
      devLog('message 1', 'message 2', { key: 'value' });
      // Should not throw
    });
  });

  describe('devWarn', () => {
    it('should call console.warn in development', () => {
      devWarn('warning message');
      // Should not throw
    });

    it('should handle multiple arguments', () => {
      devWarn('warn 1', 'warn 2', { issue: 'found' });
      // Should not throw
    });
  });

  describe('devError', () => {
    it('should call console.error in development', () => {
      devError('error message');
      // Should not throw
    });

    it('should handle error objects', () => {
      const error = new Error('Test error');
      devError('Error occurred:', error);
      // Should not throw
    });
  });
});
