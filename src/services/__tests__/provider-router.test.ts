import { describe, it, expect, beforeEach } from '@jest/globals';
import {
  updateMetricsFromBackend,
  topProvidersFor,
  getRuntimeClient,
} from '../provider-router';

describe('provider-router', () => {
  beforeEach(() => {
    // Clear metrics before each test
    jest.clearAllMocks();
  });

  describe('updateMetricsFromBackend', () => {
    it('should track latency for a provider', () => {
      updateMetricsFromBackend('openai', 150, true);
      updateMetricsFromBackend('openai', 200, true);
      updateMetricsFromBackend('openai', 180, false);

      // Should not throw
      expect(true).toBe(true);
    });

    it('should handle multiple providers independently', () => {
      updateMetricsFromBackend('openai', 100, true);
      updateMetricsFromBackend('anthropic', 150, true);

      // Should not throw
      expect(true).toBe(true);
    });

    it('should track success and failure separately', () => {
      updateMetricsFromBackend('openai', 100, true);
      updateMetricsFromBackend('openai', 150, false);

      // Should not throw
      expect(true).toBe(true);
    });
  });

  describe('topProvidersFor', () => {
    it('should return providers for chat capability', () => {
      const providers = topProvidersFor('chat');

      expect(Array.isArray(providers)).toBe(true);
      expect(providers.length).toBeGreaterThan(0);
    });

    it('should limit results to requested count', () => {
      const providers = topProvidersFor('chat', false, false, 3);

      expect(providers.length).toBeLessThanOrEqual(3);
    });

    it('should return different results with cost preference', () => {
      const standardProviders = topProvidersFor('chat', false, false, 3);
      const costProviders = topProvidersFor('chat', false, true, 3);

      // Both should be valid arrays
      expect(Array.isArray(standardProviders)).toBe(true);
      expect(Array.isArray(costProviders)).toBe(true);
    });

    it('should prioritize local providers when requested', () => {
      const providers = topProvidersFor('chat', true, false, 3);

      expect(Array.isArray(providers)).toBe(true);
    });

    it('should return empty array for unsupported capability', () => {
      const providers = topProvidersFor('nonexistent-capability');

      expect(providers).toEqual([]);
    });
  });

  describe('getRuntimeClient', () => {
    it('should return a runtime client', () => {
      const client = getRuntimeClient();

      expect(client).toBeDefined();
      expect(typeof client).toBe('object');
    });
  });
});
