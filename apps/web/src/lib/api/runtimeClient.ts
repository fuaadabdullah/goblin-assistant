import { providerKeys } from '@/lib/provider-keys';
import { streamRuntimeTask } from '@/api/runtime-stream';
import { hasMockFallbackSignal } from './fallback';
import { providersMethods } from './providers';
import { runtimeMethods } from './runtime';
import type {
  CostSummary,
  GoblinStats,
  GoblinStatus,
  MemoryEntry,
  OrchestrationPlan,
  ProviderModelOption,
  RuntimeClient,
  StreamChunk,
  TaskResponse,
  User,
} from '@/types/api';

import { apiClient } from '@/lib/api';

let runtimeConversationId: string | null = null;

const buildRuntimePrompt = (goblin: string, task: string, code?: string): string => {
  const sections = [`[goblin:${goblin}]`, task.trim()];
  if (code && code.trim()) {
    sections.push(`Code context:\n${code}`);
  }
  return sections.join('\n\n');
};

const ensureRuntimeConversation = async (): Promise<string> => {
  if (runtimeConversationId) return runtimeConversationId;
  const conversation = await apiClient.createConversation('Runtime Task Execution');
  runtimeConversationId = conversation.conversationId;
  return runtimeConversationId;
};

const runtimeClientImpl: RuntimeClient = {
  async getGoblins(): Promise<GoblinStatus[]> {
    return runtimeMethods.getGoblins();
  },

  async getProviders(): Promise<string[]> {
    return providersMethods.getProviders();
  },

  async getProviderModelOptions(provider: string): Promise<ProviderModelOption[]> {
    return providersMethods.getProviderModelOptions(provider);
  },

  async getProviderModels(provider: string): Promise<string[]> {
    return providersMethods.getProviderModels(provider);
  },

  async executeTask(
    goblin: string,
    task: string,
    streaming?: boolean,
    code?: string,
    provider?: string,
    model?: string
  ): Promise<string> {
    const conversationId = await ensureRuntimeConversation();
    const prompt = buildRuntimePrompt(goblin, task, code);
    try {
      const response = await apiClient.sendConversationMessage({
        conversationId,
        message: prompt,
        provider,
        model,
        metadata: { source: 'runtime-client', goblin },
      });
      return response.content || '';
    } catch (error) {
      const errorObj = error as any;
      const backendError =
        errorObj?.responseData?.error ||
        errorObj?.response?.data?.error ||
        errorObj?.response?.data?.detail ||
        errorObj?.response?.data?.message ||
        errorObj?.message;

      if (hasMockFallbackSignal(backendError)) {
        const fallbackResponse = await apiClient.chatCompletion(
          [{ role: 'user', content: prompt }],
          model
        );
        return typeof fallbackResponse === 'string'
          ? fallbackResponse
          : String(fallbackResponse ?? '');
      }

      throw error;
    }
  },

  async executeTaskStreaming(
    goblin: string,
    task: string,
    onChunk: (chunk: StreamChunk) => void,
    onComplete?: (response: TaskResponse) => void,
    code?: string,
    provider?: string,
    model?: string
  ): Promise<void> {
    const conversationId = await ensureRuntimeConversation();
    const prompt = buildRuntimePrompt(goblin, task, code);
    await streamRuntimeTask(
      {
        conversationId,
        prompt,
        provider,
        model,
        goblin,
      },
      {
        onChunk,
        onComplete,
      }
    );
  },

  async setProviderApiKey(provider: string, key: string): Promise<void> {
    providerKeys.set(provider, key);
  },

  async storeApiKey(provider: string, key: string): Promise<void> {
    providerKeys.set(provider, key);
  },

  async getApiKey(provider: string): Promise<string | null> {
    return providerKeys.get(provider);
  },

  async clearApiKey(provider: string): Promise<void> {
    providerKeys.remove(provider);
  },

  async getHistory(goblin: string, limit?: number): Promise<MemoryEntry[]> {
    return runtimeMethods.getHistory(goblin, limit);
  },

  async getStats(goblin: string): Promise<GoblinStats> {
    return runtimeMethods.getStats(goblin);
  },

  async getCostSummary(): Promise<CostSummary> {
    return providersMethods.getCostSummary();
  },

  async parseOrchestration(text: string, defaultGoblin?: string): Promise<OrchestrationPlan> {
    return runtimeMethods.parseOrchestration(text, defaultGoblin);
  },

  async onTaskStream(): Promise<void> {},

  async login(email: string, password: string): Promise<{ token: string; user: User }> {
    const result = await apiClient.login(email, password);
    return {
      token: String((result as { token?: string; access_token?: string }).token ?? (result as { token?: string; access_token?: string }).access_token ?? ''),
      user: (result as { user?: User }).user as User,
    };
  },

  async register(email: string, password: string): Promise<{ token: string; user: User }> {
    const result = await apiClient.register(email, password);
    return {
      token: String((result as { token?: string; access_token?: string }).token ?? (result as { token?: string; access_token?: string }).access_token ?? ''),
      user: (result as { user?: User }).user as User,
    };
  },

  async logout(): Promise<void> {
    await apiClient.logout().catch(() => {});
  },

  async validateToken(token: string): Promise<{ valid: boolean; user?: User | undefined }> {
    const result = await apiClient.validateToken(token);
    return { valid: result?.valid ?? false, user: result?.user };
  },
};

export const runtimeClient = runtimeClientImpl;
export const runtimeClientDemo = runtimeClientImpl;
