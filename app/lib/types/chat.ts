// lib/types/chat.ts
export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: Date;
  isPartial?: boolean;
  metadata?: {
    provider?: string;
    model?: string;
    tokens?: number;
    cost?: number;
    latency?: number;
  };
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  isActive: boolean;
  metadata?: {
    totalTokens?: number;
    totalCost?: number;
    providerUsage?: Record<string, number>;
  };
}

export interface ChatRequest {
  message: string;
  sessionId?: string;
  provider?: string;
  model?: string;
  temperature?: number;
  maxTokens?: number;
  stream?: boolean;
}

export interface ChatResponse {
  message: Message;
  sessionId: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
    cost: number;
  };
}

export interface StreamingChunk {
  content: string;
  done: boolean;
  metadata?: {
    provider: string;
    model: string;
    tokensUsed?: number;
  };
}
