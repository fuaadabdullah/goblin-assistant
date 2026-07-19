import { getFrontend, postFrontend } from './shared';
import type { GoblinStats, GoblinStatus, MemoryEntry, OrchestrationPlan } from '../../types/api';

const INTERNAL_RUNTIME_PREFIX = '/api/runtime';

export const runtimeMethods = {
  async getGoblins(): Promise<GoblinStatus[]> {
    return getFrontend<GoblinStatus[]>(`${INTERNAL_RUNTIME_PREFIX}/goblins`);
  },

  async getHistory(goblin: string, limit = 10): Promise<MemoryEntry[]> {
    const cappedLimit = Math.max(1, Math.min(Number(limit) || 10, 100));
    return getFrontend<MemoryEntry[]>(
      `${INTERNAL_RUNTIME_PREFIX}/history/${encodeURIComponent(goblin)}?limit=${cappedLimit}`
    );
  },

  async getStats(goblin: string): Promise<GoblinStats> {
    return getFrontend<GoblinStats>(
      `${INTERNAL_RUNTIME_PREFIX}/stats/${encodeURIComponent(goblin)}`
    );
  },

  async parseOrchestration(text: string, defaultGoblin?: string): Promise<OrchestrationPlan> {
    return postFrontend<OrchestrationPlan, { text: string; default_goblin?: string | undefined }>(
      `${INTERNAL_RUNTIME_PREFIX}/orchestrate/parse`,
      {
        text,
        default_goblin: defaultGoblin,
      }
    );
  },
};
