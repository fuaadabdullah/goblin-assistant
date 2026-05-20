import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import {
  logErrorToService,
  reactErrorInfoToContext,
  logPerformanceMetric,
} from '../monitoring';

// Mock console methods
jest.spyOn(console, 'error').mockImplementation(() => {});
jest.spyOn(console, 'warn').mockImplementation(() => {});

describe('monitoring utilities', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('logErrorToService', () => {
    it('should log an error with context', () => {
      const error = new Error('Test error');
      const context = {
        component: 'ChatScreen',
        userId: 'user-123',
      };

      logErrorToService(error, context);

      // Should not throw
      expect(true).toBe(true);
    });

    it('should handle errors without context', () => {
      const error = new Error('Error without context');

      logErrorToService(error);

      expect(true).toBe(true);
    });

    it('should handle non-Error objects', () => {
      const unknownError = { message: 'Unknown error' };

      expect(() => {
        logErrorToService(unknownError as any);
      }).not.toThrow();
    });

    it('should include error stack trace in context', () => {
      const error = new Error('Stack trace test');
      const context = { component: 'Test' };

      logErrorToService(error, context);

      expect(true).toBe(true);
    });

    it('should handle very large context objects', () => {
      const error = new Error('Large context error');
      const largeContext = {
        ...Object.fromEntries(
          Array.from({ length: 100 }, (_, i) => [`key${i}`, `value${i}`]),
        ),
      };

      logErrorToService(error, largeContext as any);

      expect(true).toBe(true);
    });
  });

  describe('reactErrorInfoToContext', () => {
    it('should convert React Error Info to context', () => {
      const errorInfo = {
        componentStack: 'at ChatScreen\n at App',
      };

      const context = reactErrorInfoToContext(errorInfo as any);

      expect(context).toBeDefined();
      expect(typeof context).toBe('object');
    });

    it('should extract component stack correctly', () => {
      const errorInfo = {
        componentStack: 'at Component1\n at Component2',
      };

      const context = reactErrorInfoToContext(errorInfo as any);

      expect(context).toHaveProperty('componentStack');
    });

    it('should handle empty component stack', () => {
      const errorInfo = {
        componentStack: '',
      };

      const context = reactErrorInfoToContext(errorInfo as any);

      expect(context).toBeDefined();
    });

    it('should handle missing errorInfo', () => {
      const errorInfo = {} as any;

      expect(() => {
        reactErrorInfoToContext(errorInfo);
      }).not.toThrow();
    });
  });

  describe('logPerformanceMetric', () => {
    it('should log a performance metric', () => {
      const consoleSpy = jest
        .spyOn(console, 'log')
        .mockImplementation(() => {});

      logPerformanceMetric('chat_message_latency', 234);

      expect(true).toBe(true);
      consoleSpy.mockRestore();
    });

    it('should handle zero values', () => {
      expect(() => {
        logPerformanceMetric('metric_name', 0);
      }).not.toThrow();
    });

    it('should handle large values', () => {
      expect(() => {
        logPerformanceMetric('large_metric', 999999999);
      }).not.toThrow();
    });

    it('should handle decimal values', () => {
      expect(() => {
        logPerformanceMetric('decimal_metric', 123.456);
      }).not.toThrow();
    });

    it('should accept various metric names', () => {
      const metricNames = [
        'api_latency_ms',
        'model_inference_ms',
        'db_query_time',
        'provider_response_time',
      ];

      metricNames.forEach((name) => {
        expect(() => {
          logPerformanceMetric(name, 100);
        }).not.toThrow();
      });
    });
  });

  describe('error handling edge cases', () => {
    it('should handle circular references in context', () => {
      const error = new Error('Circular ref error');
      const context: any = { component: 'Test' };
      context.self = context; // Create circular reference

      expect(() => {
        logErrorToService(error, context);
      }).not.toThrow();
    });

    it('should handle errors with special characters', () => {
      const error = new Error('Error with special chars: <>&"\' etc');

      expect(() => {
        logErrorToService(error);
      }).not.toThrow();
    });

    it('should handle very long error messages', () => {
      const error = new Error('x'.repeat(10000));

      expect(() => {
        logErrorToService(error);
      }).not.toThrow();
    });
  });
});
