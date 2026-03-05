// lib/types/providers.ts
export type ProviderType = 'openai' | 'anthropic' | 'groq' | 'deepseek' | 'ollama' | 'generic';

export interface ProviderConfig {
  id: string;
  name: string;
  type: ProviderType;
  baseUrl?: string;
  apiKey?: string;
  models: ModelConfig[];
  isEnabled: boolean;
  priority: number;
  rateLimits?: {
    requestsPerMinute: number;
    tokensPerMinute: number;
  };
  costConfig?: {
    inputCostPerToken: number;
    outputCostPerToken: number;
    currency: string;
  };
}

export interface ModelConfig {
  id: string;
  name: string;
  contextWindow: number;
  maxTokens: number;
  supportsStreaming: boolean;
  capabilities: ModelCapability[];
  costPerToken?: {
    input: number;
    output: number;
  };
}

export interface ModelCapability {
  type: 'chat' | 'completion' | 'embedding' | 'image' | 'audio';
  quality: 'low' | 'medium' | 'high';
}

export interface ProviderHealth {
  providerId: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency: number;
  lastChecked: Date;
  errorCount: number;
  circuitBreaker?: {
    isOpen: boolean;
    failureCount: number;
    lastFailureTime?: Date;
  };
}

export interface RoutingStrategy {
  type: 'cost-optimized' | 'performance' | 'balanced' | 'manual';
  preferences?: {
    maxCostPerRequest?: number;
    maxLatency?: number;
    preferredProviders?: string[];
    fallbackProviders?: string[];
  };
}

export interface ComplexityAnalysis {
  level: 'simple' | 'medium' | 'complex';
  estimatedTokens: number;
  requiresReasoning: boolean;
  suggestedProviders: string[];
}
