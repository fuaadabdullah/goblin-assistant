import {
  APIError,
  NetworkError,
  ValidationError,
  withErrorTracking,
  trackApiCall,
  trackLLMOperation,
} from '../error-tracking';

describe('Error Tracking', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Custom Error Classes', () => {
    it('should create APIError with correct message', () => {
      const error = new APIError('API failed', 500, { error: 'Internal' });
      expect(error.message).toBe('API failed');
      expect(error.status).toBe(500);
      expect(error.data).toEqual({ error: 'Internal' });
    });

    it('should create NetworkError with correct message', () => {
      const error = new NetworkError('Network timeout', 'timeout');
      expect(error.message).toBe('Network timeout');
      expect(error.code).toBe('timeout');
    });

    it('should create ValidationError with correct message', () => {
      const error = new ValidationError('Invalid input', ['field1', 'field2']);
      expect(error.message).toBe('Invalid input');
      expect(error.fields).toEqual(['field1', 'field2']);
    });
  });

  describe('withErrorTracking', () => {
    it('should execute function and return result', async () => {
      const mockFn = jest.fn().mockResolvedValue('success');
      const result = await withErrorTracking(mockFn, 'test-operation');
      expect(result).toBe('success');
      expect(mockFn).toHaveBeenCalled();
    });

    it('should handle errors and retry by default', async () => {
      const mockFn = jest
        .fn()
        .mockRejectedValueOnce(new Error('First attempt'))
        .mockResolvedValueOnce('success');

      const result = await withErrorTracking(mockFn, 'test-operation', {
        maxRetries: 2,
      });
      expect(result).toBe('success');
    });

    it('should throw after max retries exceeded', async () => {
      const mockFn = jest.fn().mockRejectedValue(new Error('Always fails'));

      await expect(
        withErrorTracking(mockFn, 'test-operation', { maxRetries: 2 }),
      ).rejects.toThrow();
    });

    it('should respect timeout parameter', async () => {
      const slowFn = jest.fn(
        () => new Promise((resolve) => setTimeout(resolve, 10000)),
      );

      await expect(
        withErrorTracking(slowFn, 'test-operation', { timeout: 100 }),
      ).rejects.toThrow();
    });
  });

  describe('trackApiCall', () => {
    it('should success fully execute and track API call', async () => {
      const mockFn = jest.fn().mockResolvedValue({ data: 'response' });
      const result = await trackApiCall(mockFn, 'GET', '/api/test');

      expect(result).toEqual({ data: 'response' });
      expect(mockFn).toHaveBeenCalled();
    });

    it('should handle API errors appropriately', async () => {
      const mockFn = jest
        .fn()
        .mockRejectedValue(new APIError('Not found', 404));

      await expect(trackApiCall(mockFn, 'GET', '/api/missing')).rejects.toThrow(
        APIError,
      );
    });
  });

  describe('trackLLMOperation', () => {
    it('should track LLM operation successfully', async () => {
      const mockFn = jest.fn().mockResolvedValue({ tokens: 100 });
      const result = await trackLLMOperation(mockFn, 'openai', 'gpt-4');

      expect(result).toEqual({ tokens: 100 });
    });

    it('should handle LLM operation failures', async () => {
      const mockFn = jest.fn().mockRejectedValue(new Error('LLM unavailable'));

      await expect(
        trackLLMOperation(mockFn, 'openai', 'gpt-4'),
      ).rejects.toThrow();
    });
  });
});
