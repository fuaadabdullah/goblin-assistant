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
}

export interface ChatMessage {
  id: string;
  createdAt: string;
  role: ChatRole;
  content: string;
  meta?: ChatMessageMeta;
}

export interface ChatThread {
  id: string;
  title: string;
  snippet: string;
  createdAt: string;
  updatedAt: string;
}
