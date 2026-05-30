import { getBackend, devWarn } from './shared';
import type { HealthStatus } from '../../types/api';

export const healthMethods = {
  async getAllHealth(): Promise<HealthStatus> {
    try {
      return await getBackend<HealthStatus>('/health');
    } catch (error) {
      devWarn('Health check failed:', error);
      return {
        overall: 'unhealthy',
        timestamp: new Date().toISOString(),
        services: {},
      };
    }
  },

  async getStreamingHealth() {
    try {
      return await getBackend('/health/streaming');
    } catch (error) {
      devWarn('Streaming health check failed:', error);
      return { status: 'unknown' };
    }
  },

  async getRoutingHealth() {
    try {
      return await getBackend('/health/routing');
    } catch (error) {
      devWarn('Routing health check failed:', error);
      return { status: 'unknown' };
    }
  },

  async getRoutingInfo() {
    return getBackend('/routing/info');
  },
};
