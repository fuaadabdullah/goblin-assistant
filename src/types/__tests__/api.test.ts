import { describe, it, expect } from '@jest/globals';
import {
  isApiError,
  isApiSuccess,
  isHealthStatus,
  isOrchestrationPlan,
  isTaskExecutionResponse,
  isChatCompletionResponse,
} from '../api';

describe('API type guards', () => {
  describe('isApiError', () => {
    it('should identify valid error responses', () => {
      const error = {
        success: false,
        error: 'Something went wrong',
        code: 'E_INTERNAL',
      };

      expect(isApiError(error)).toBe(true);
    });

    it('should reject non-error responses', () => {
      const success = {
        success: true,
        data: {},
      };

      expect(isApiError(success)).toBe(false);
    });

    it('should handle null/undefined', () => {
      expect(isApiError(null)).toBe(false);
      expect(isApiError(undefined)).toBe(false);
    });

    it('should reject non-objects', () => {
      expect(isApiError('error')).toBe(false);
      expect(isApiError(123)).toBe(false);
    });
  });

  describe('isApiSuccess', () => {
    it('should identify valid success responses', () => {
      const success = {
        success: true,
        data: { message: 'OK' },
      };

      expect(isApiSuccess(success)).toBe(true);
    });

    it('should reject error responses', () => {
      const error = {
        success: false,
        error: 'Error',
      };

      expect(isApiSuccess(error)).toBe(false);
    });

    it('should handle null/undefined', () => {
      expect(isApiSuccess(null)).toBe(false);
      expect(isApiSuccess(undefined)).toBe(false);
    });
  });

  describe('isHealthStatus', () => {
    it('should identify valid health status', () => {
      const health = {
        status: 'healthy',
        timestamp: '2026-02-18T10:00:00Z',
        uptime_ms: 3600000,
      };

      expect(isHealthStatus(health)).toBe(true);
    });

    it('should accept different status values', () => {
      const health = {
        status: 'degraded',
        timestamp: '2026-02-18T10:00:00Z',
      };

      expect(isHealthStatus(health)).toBe(true);
    });

    it('should reject invalid health status', () => {
      const invalid = { message: 'OK' };

      expect(isHealthStatus(invalid)).toBe(false);
    });
  });

  describe('isOrchestrationPlan', () => {
    it('should identify valid orchestration plan', () => {
      const plan = {
        id: 'plan-123',
        steps: [{ id: 'step-1', type: 'execute', action: 'analyze' }],
        estimated_duration_ms: 5000,
      };

      expect(isOrchestrationPlan(plan)).toBe(true);
    });

    it('should handle empty steps', () => {
      const plan = {
        id: 'plan-123',
        steps: [],
      };

      expect(isOrchestrationPlan(plan)).toBe(true);
    });

    it('should reject invalid plans', () => {
      const invalid = { steps: 'not-an-array' };

      expect(isOrchestrationPlan(invalid)).toBe(false);
    });
  });

  describe('isTaskExecutionResponse', () => {
    it('should identify valid task execution response', () => {
      const response = {
        task_id: 'task-123',
        status: 'completed',
        result: { output: 'Success' },
      };

      expect(isTaskExecutionResponse(response)).toBe(true);
    });

    it('should accept different statuses', () => {
      const response = {
        task_id: 'task-456',
        status: 'in_progress',
      };

      expect(isTaskExecutionResponse(response)).toBe(true);
    });

    it('should reject invalid responses', () => {
      const invalid = { message: 'Not a task' };

      expect(isTaskExecutionResponse(invalid)).toBe(false);
    });
  });

  describe('isChatCompletionResponse', () => {
    it('should identify valid chat completion', () => {
      const response = {
        id: 'chat-123',
        content: 'Hello! How can I help?',
        model: 'gpt-4o-mini',
        usage: {
          prompt_tokens: 10,
          completion_tokens: 5,
          total_tokens: 15,
        },
      };

      expect(isChatCompletionResponse(response)).toBe(true);
    });

    it('should accept different content types', () => {
      const response = {
        id: 'chat-456',
        content: 'Response',
        model: 'gpt-4-turbo',
      };

      expect(isChatCompletionResponse(response)).toBe(true);
    });

    it('should reject invalid responses', () => {
      const invalid = { message: 'Not a chat response' };

      expect(isChatCompletionResponse(invalid)).toBe(false);
    });

    it('should validate content is string', () => {
      const invalid = {
        id: 'chat-789',
        content: { nested: 'object' },
      };

      expect(isChatCompletionResponse(invalid)).toBe(false);
    });
  });
});
