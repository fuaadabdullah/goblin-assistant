'use client';

import { apiClient } from '@/lib/api';

type BackendProvider = {
  id?: string | number;
  name?: string;
  description?: string;
  enabled?: boolean;
  health?: string;
  status?: string;
  type?: string;
  cost_per_input_token?: number;
  cost_per_output_token?: number;
  models?: Array<{ id?: string; name?: string; max_tokens?: number; description?: string }>;
  updated_at?: string;
};

type HealthResponse = {
  services?: Record<string, { status?: string; checked_at?: string }>;
  providers?: Record<string, { status?: string; checked_at?: string }>;
  timestamp?: string;
};

export const providerService = {
  getProviders: async () => {
    const raw = (await apiClient.getProviderSettings()) as BackendProvider[] | null;
    const list = Array.isArray(raw) ? raw : [];
    return list.map((p) => ({
      id: String(p.id ?? p.name ?? ''),
      name: p.name ?? String(p.id ?? ''),
      description: p.description ?? '',
      isAvailable: p.enabled !== false,
      type: p.type ?? '',
      costConfig: {
        inputCostPerToken: p.cost_per_input_token ?? 0,
        outputCostPerToken: p.cost_per_output_token ?? 0,
      },
      models: (p.models ?? []).map((m) => ({
        id: m.id ?? m.name ?? '',
        name: m.name ?? m.id ?? '',
        providerId: String(p.id ?? p.name ?? ''),
        maxTokens: m.max_tokens ?? 4096,
        description: m.description ?? '',
        isAvailable: true,
      })),
    }));
  },

  getProviderHealth: async () => {
    const health = (await apiClient.getRoutingHealth()) as HealthResponse | null;
    const now = new Date().toISOString();
    const sources: Record<string, { status?: string; checked_at?: string }> = {
      ...(health?.services ?? {}),
      ...(health?.providers ?? {}),
    };
    return Object.fromEntries(
      Object.entries(sources).map(([key, val]) => [
        key,
        { status: val?.status ?? 'unknown', lastChecked: val?.checked_at ?? now },
      ]),
    );
  },

  getProviderStatus: async (providerId: string) => {
    try {
      const result = (await apiClient.testProviderConnection(providerId)) as { status?: string; latency_ms?: number } | null;
      return {
        status: result?.status ?? 'available',
        lastChecked: new Date().toISOString(),
        responseTime: result?.latency_ms ?? 0,
      };
    } catch {
      return { status: 'unavailable', lastChecked: new Date().toISOString(), responseTime: 0 };
    }
  },
};
