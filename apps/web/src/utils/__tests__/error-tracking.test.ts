import {
  APIError,
  NetworkError,
  ValidationError,
  withErrorTracking,
  trackApiCall,
  trackLLMOperation,
  trackRoutingOperation,
  trackUserAction,
  trackPerformance,
  logComponentError,
  setupGlobalErrorTracking,
} from '../error-tracking';

describe('Error Tracking', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Custom Error Classes', () => {
    it('should create APIError with correct properties', () => {
      const error = new APIError('API failed', 500, '/api/test', 'GET', { extra: true });
      expect(error.message).toBe('API failed');
      expect(error.statusCode).toBe(500);
      expect(error.endpoint).toBe('/api/test');
      expect(error.method).toBe('GET');
      expect(error.context).toEqual({ extra: true });
      expect(error.name).toBe('APIError');
      expect(error).toBeInstanceOf(Error);
    });

    it('should create NetworkError with correct properties', () => {
      const original = new Error('connection reset');
      const error = new NetworkError('Network timeout', '/api/health', original);
      expect(error.message).toBe('Network timeout');
      expect(error.endpoint).toBe('/api/health');
      expect(error.originalError).toBe(original);
      expect(error.name).toBe('NetworkError');
    });

    it('should create ValidationError with correct properties', () => {
      const error = new ValidationError('Invalid input', 'email', 'bad@');
      expect(error.message).toBe('Invalid input');
      expect(error.field).toBe('email');
      expect(error.value).toBe('bad@');
      expect(error.name).toBe('ValidationError');
    });
  });

  describe('withErrorTracking', () => {
    it('should execute function and return result', async () => {
      const mockFn = jest.fn().mockResolvedValue('success');
      const result = await withErrorTracking(mockFn, { operation: 'test-op' });
      expect(result).toBe('success');
      expect(mockFn).toHaveBeenCalled();
    });

    it('should rethrow errors from the operation', async () => {
      const mockFn = jest.fn().mockRejectedValue(new Error('fail'));
      await expect(
        withErrorTracking(mockFn, { operation: 'test-op' }),
      ).rejects.toThrow('fail');
    });

    it('should wrap non-Error throws', async () => {
      const mockFn = jest.fn().mockRejectedValue('string error');
      await expect(
        withErrorTracking(mockFn, { operation: 'test-op' }),
      ).rejects.toThrow('Operation failed');
    });
  });

  describe('trackApiCall', () => {
    it('should execute and track successful API call', async () => {
      const mockFn = jest.fn().mockResolvedValue({ data: 'response' });
      const result = await trackApiCall(mockFn, '/api/test', 'GET');
      expect(result).toEqual({ data: 'response' });
      expect(mockFn).toHaveBeenCalled();
    });

    it('should handle API errors appropriately', async () => {
      const mockFn = jest.fn().mockRejectedValue(new APIError('Not found', 404));
      await expect(trackApiCall(mockFn, '/api/missing', 'GET')).rejects.toThrow(APIError);
    });
  });

  describe('trackLLMOperation', () => {
    it('should track LLM operation successfully', async () => {
      const mockFn = jest.fn().mockResolvedValue({ tokens: 100 });
      const result = await trackLLMOperation(mockFn, {
        provider: 'openai', model: 'gpt-4', operation: 'chat',
      });
      expect(result).toEqual({ tokens: 100 });
    });

    it('should handle LLM operation failures', async () => {
      const mockFn = jest.fn().mockRejectedValue(new Error('LLM unavailable'));
      await expect(
        trackLLMOperation(mockFn, {
          provider: 'openai', model: 'gpt-4', operation: 'chat',
        }),
      ).rejects.toThrow();
    });
  });

  describe('trackRoutingOperation', () => {
    it('should track routing decisions', () => {
      expect(() => {
        trackRoutingOperation('openai', 'anthropic', 'rate_limit');
      }).not.toThrow();
    });
  });

  describe('trackUserAction', () => {
    it('should log user actions', () => {
      expect(() => { trackUserAction('click_send'); }).not.toThrow();
    });
  });

  describe('trackPerformance', () => {
    it('should log performance metrics', () => {
      expect(() => { trackPerformance('ttfb', 250); }).not.toThrow();
    });
  });

  describe('logComponentError', () => {
    it('should log component errors', () => {
      expect(() => {
        logComponentError(
          new Error('render failed'),
          { componentStack: '<App>' },
          'TestComponent',
        );
      }).not.toThrow();
    });
  });

  describe('setupGlobalErrorTracking', () => {
    it('should not throw when called', () => {
      expect(() => { setupGlobalErrorTracking(); }).not.toThrow();
    });
  });
});
