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

export interface AgentTaskSubmitPayload {
  task: string;
  repo_url?: string | undefined;
  base_branch?: string | undefined;
  branch_name?: string | undefined;
  tests_command?: string | undefined;
  source?: string | undefined;
  issue_url?: string | undefined;
  issue_number?: number | undefined;
  issue_title?: string | undefined;
  issue_body?: string | undefined;
  metadata?: Record<string, unknown> | undefined;
}

export interface AgentTaskEvent {
  event_id: string;
  type: string;
  message: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface AgentTaskRecord {
  task_id: string;
  status: string;
  phase: string;
  source: string;
  task: string;
  repo_url: string;
  base_branch: string;
  branch_name: string;
  tests_command: string;
  issue_url?: string | null;
  issue_number?: number | null;
  issue_title?: string | null;
  issue_body?: string | null;
  worker_status?: string | null;
  worker_error?: string | null;
  pr_url?: string | null;
  callback_url?: string | null;
  workspace_id?: string | null;
  workspace_family?: string | null;
  sprite_name?: string | null;
  checkout_ref?: string | null;
  workspace_provider?: string | null;
  architect_model?: string | null;
  editor_model?: string | null;
  aider_mode?: string | null;
  auto_commit_each_change?: boolean | null;
  repair_attempts?: number | null;
  phase0_ci_commands?: Array<Record<string, unknown>>;
  workspace?: Record<string, unknown>;
  worker_profile?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  events: AgentTaskEvent[];
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
  result: Record<string, unknown>;
}

export interface AgentTaskEventsResponse {
  task_id: string;
  status: string;
  phase: string;
  events: AgentTaskEvent[];
  total: number;
}

export interface AgentTaskStatusResponse {
  task: AgentTaskRecord;
}

export interface AgentTaskWebhookResponse {
  accepted: boolean;
  ignored?: boolean;
  reason?: string | null;
  task?: AgentTaskRecord | null;
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

export interface AccountPreferencesRecord {
  theme?: string | null;
  default_model?: string | null;
  default_provider?: string | null;
  notifications_enabled?: boolean;
  language?: string | null;
  other?: Record<string, unknown>;
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

export type {
  ModelUsageRollup,
  ModelUsageRollupResponse,
  ModelUsageRollupSummary,
} from '../../types/api';
