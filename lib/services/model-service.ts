'use client';

import { apiClient } from '@/lib/api';

type ModelEntry = {
  id?: string;
  name?: string;
  provider?: string;
  max_tokens?: number;
  description?: string;
  is_selectable?: boolean;
};

type ModelRegistryResponse = {
  models?: ModelEntry[];
};

const COMPLEXITY_KEYWORDS: Record<'simple' | 'medium' | 'complex', string[]> = {
  complex: ['gpt-4', 'claude-3-opus', 'claude-3-5', 'claude-3.5', 'gemini-pro', 'gpt-4o'],
  medium: ['gpt-4', 'claude-3-haiku', 'claude-3-sonnet', 'gemini'],
  simple: [],
};

export const modelService = {
  getAvailableModels: async () => {
    const registry = (await apiClient.getModelConfigs()) as ModelRegistryResponse;
    const models = (registry?.models ?? []).map((m) => ({
      id: m.id ?? m.name ?? '',
      name: m.name ?? m.id ?? '',
      provider: m.provider ?? '',
      maxTokens: m.max_tokens ?? 4096,
      description: m.description ?? '',
    }));
    return { success: true, models };
  },

  getRecommendedModel: async (taskType: 'simple' | 'medium' | 'complex' = 'medium') => {
    const { models } = await modelService.getAvailableModels();
    const keywords = COMPLEXITY_KEYWORDS[taskType] ?? [];
    const match =
      keywords.length > 0
        ? models.find((m) => keywords.some((kw) => m.id.toLowerCase().includes(kw)))
        : undefined;
    const modelId = match?.id ?? models[0]?.id ?? '';
    return { success: true, modelId };
  },

  getModelStatus: async (modelId: string) => {
    const providers = (await apiClient.getProviderSettings()) as Array<{ id?: string; name?: string; status?: string; health?: string; updated_at?: string }> | null;
    const list = Array.isArray(providers) ? providers : [];
    const provider = list.find((p) =>
      modelId.toLowerCase().includes((p.id ?? p.name ?? '').toLowerCase()),
    );
    const status = provider?.status ?? provider?.health ?? 'available';
    return {
      success: true,
      status,
      lastUsed: new Date().toISOString(),
      usageCount: 0,
    };
  },
};
