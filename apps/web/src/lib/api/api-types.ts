/**
 * API Types
 *
 * Type definitions used across the API client layer.
 * Extracted from the former shared.ts modularization.
 */

import type { ChatMessage as DomainChatMessage, ChatUsage } from '../../domain/chat';
import type {
  ChatMessage,
  ChatCompletionResponse,
  HealthStatus,
  ValidateTokenResponse,
} from '../../types/api';

// ============================================================================
// Request/Response Types
// ============================================================================

export interface ProviderUpdatePayload {
  name?: string;
  enabled?: boolean;
  priority?: number;
  weight?: number;
  api_key?: string;
  base_url?: string;
  models?: string[];
}

export interface PasskeyCredential {
  id: string;
  rawId: string;
  type: string;
  response: {
    attestationObject?: string;
    clientDataJSON: string;
    authenticatorData?: string;
    signature?: string;
  };
}

export interface SandboxRunPayload {
  code?: string;
  source?: string;
  language?: string;
  timeout?: number;
}

export interface AccountProfile {
  name?: string;
  email?: string;
  avatar_url?: string;
}

export interface AccountPreferences {
  theme?: string;
  default_model?: string;
  default_provider?: string;
  [key: string]: string | boolean | number | undefined;
}

export interface ConversationCreateResponse {
  conversation_id: string;
  title: string;
  created_at: string;
}

export interface ConversationInfoResponse {
  conversation_id: string;
  user_id?: string | null;
  title: string;
  message_count: number;
  snippet?: string | null;
  created_at: string;
  updated_at: string;
  category?: string | null;
}

export interface ConversationDetailResponse {
  conversation_id: string;
  user_id?: string | null;
  title: string;
  messages: Array<{
    message_id: string;
    role: DomainChatMessage['role'];
    content: string;
    timestamp: string;
    metadata?: DomainChatMessage['meta'];
  }>;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
  pagination?: {
    total?: number;
    offset?: number;
    limit?: number;
    has_more?: boolean;
  };
}

export interface ConversationSendResponse {
  message_id: string;
  response: string;
  department?: string; // Which brain department handled this
  department_reason?: string; // Why this department was chosen
  provider: string; // Internal: deprecated, use department
  model: string; // Internal: deprecated, use department
  timestamp: string;
  usage?: ChatUsage;
  cost_usd?: number;
  correlation_id?: string;
  visualizations?: Array<{
    type: string;
    title: string;
    data: Record<string, unknown>[];
    config: Record<string, unknown>;
  }>;
}

export interface StandardApiErrorPayload {
  code?: string;
  type?: string;
  message?: string;
  request_id?: string;
  timestamp?: string;
  trace_id?: string;
  details?: Record<string, unknown>;
}

export interface StandardApiEnvelope<T> {
  success: boolean;
  data?: T;
  error?: StandardApiErrorPayload | string;
}

// Re-export types from other modules for convenience
export type {
  DomainChatMessage,
  ChatUsage,
  ChatMessage,
  ChatCompletionResponse,
  HealthStatus,
  ValidateTokenResponse,
};
