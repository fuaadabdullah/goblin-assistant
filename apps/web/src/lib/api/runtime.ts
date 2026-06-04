import { V1_API_PREFIX, getBackend, postBackend } from './shared';
import type { GoblinStats, GoblinStatus, MemoryEntry, OrchestrationPlan } from '../../types/api';

export const runtimeMethods = {
  async getGoblins(): Promise<GoblinStatus[]> {
    return getBackend<GoblinStatus[]>(`${V1_API_PREFIX}/api/goblins`);
  },

  async getHistory(goblin: string, limit = 10): Promise<MemoryEntry[]> {
    const cappedLimit = Math.max(1, Math.min(Number(limit) || 10, 100));
    return getBackend<MemoryEntry[]>(
      `${V1_API_PREFIX}/api/history/${encodeURIComponent(goblin)}?limit=${cappedLimit}`
    );
  },

  async getStats(goblin: string): Promise<GoblinStats> {
    return getBackend<GoblinStats>(`${V1_API_PREFIX}/api/stats/${encodeURIComponent(goblin)}`);
  },

  async parseOrchestration(text: string, defaultGoblin?: string): Promise<OrchestrationPlan> {
    return postBackend<OrchestrationPlan, { text: string; default_goblin?: string }>(
      `${V1_API_PREFIX}/api/orchestrate/parse`,
      {
        text,
        default_goblin: defaultGoblin,
      }
    );
  },
};
