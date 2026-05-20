export type ChatRole = 'user' | 'assistant' | 'system';

export interface ChatUsage {
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
}

export interface ChatMessageMeta {
  provider?: string;
  model?: string;
  usage?: ChatUsage;
  cost_usd?: number;
  // UI-side estimates (pre-send).
  estimated_cost_usd?: number;
  estimated_tokens?: number;
  // Trace/debugging.
  correlation_id?: string;
  // When cost is computed client-side (fallback), mark it clearly.
  cost_is_approx?: boolean;
  // File attachments associated with this message.
  attachments?: Array<{
    id: string;
    filename: string;
    mime_type: string;
    size_bytes: number;
  }>;
  // Financial visualizations (charts, tables) from tool execution.
  visualizations?: Array<{
    type: string;
    title: string;
    data: Record<string, unknown>[];
    config: Record<string, unknown>;
  }>;
}

export interface ChatMessage {
  id: string;
  createdAt: string;
  role: ChatRole;
  content: string;
  meta?: ChatMessageMeta;
  // UI-side streaming indicator
  isStreaming?: boolean;
}

export type ChatThreadSource = 'backend' | 'legacy-local';

export interface ChatThread {
  id: string;
  threadKey: string;
  source: ChatThreadSource;
  title: string;
  snippet: string;
  createdAt: string;
  updatedAt: string;
}
