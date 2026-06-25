import { providerKeys } from '@/lib/provider-keys';
import { streamRuntimeTask } from '@/api/runtime-stream';
import { hasMockFallbackSignal } from './fallback';
import type {
  CostSummary,
  GoblinStats,
  GoblinStatus,
  LoginResponse,
  MemoryEntry,
  OrchestrationPlan,
  ProviderModelOption,
  RuntimeClient,
  StreamChunk,
  TaskResponse,
  User,
} from '@/types/api';

import { apiClient, V1_CHAT_PREFIX } from '@/lib/api';

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
    return apiClient.getGoblins();
  },

  async getProviders(): Promise<string[]> {
    return apiClient.getProviders();
  },

  async getProviderModelOptions(provider: string): Promise<ProviderModelOption[]> {
    return apiClient.getProviderModelOptions(provider);
  },

  async getProviderModels(provider: string): Promise<string[]> {
    return apiClient.getProviderModels(provider);
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
    return apiClient.getHistory(goblin, limit);
  },

  async getStats(goblin: string): Promise<GoblinStats> {
    return apiClient.getStats(goblin);
  },

  async getCostSummary(): Promise<CostSummary> {
    return apiClient.getCostSummary();
  },

  async parseOrchestration(text: string, defaultGoblin?: string): Promise<OrchestrationPlan> {
    return apiClient.parseOrchestration(text, defaultGoblin);
  },

  async onTaskStream(): Promise<void> {},

  async login(email: string, password: string): Promise<LoginResponse> {
    return apiClient.login(email, password) as Promise<LoginResponse>;
  },

  async register(email: string, password: string): Promise<LoginResponse> {
    return apiClient.register(email, password) as Promise<LoginResponse>;
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
