export type ChatRole = 'user' | 'assistant' | 'system';

export interface ChatUsage {
  input_tokens?: number | undefined;
  output_tokens?: number | undefined;
  total_tokens?: number | undefined;
}

export interface ChatMessageMeta {
  department?: string | undefined; // Which brain department handled this
  department_reason?: string | undefined; // Why this department was chosen
  provider?: string | undefined; // Internal: deprecated, use department
  model?: string | undefined; // Internal: deprecated, use department
  usage?: ChatUsage | undefined;
  cost_usd?: number | undefined;
  // UI-side estimates (pre-send).
  estimated_cost_usd?: number | undefined;
  estimated_tokens?: number | undefined;
  // Trace/debugging.
  correlation_id?: string | undefined;
  // When cost is computed client-side (fallback), mark it clearly.
  cost_is_approx?: boolean | undefined;
  // File attachments associated with this message.
  attachments?:
    | Array<{
        id: string;
        filename: string;
        mime_type: string;
        size_bytes: number;
      }>
    | undefined;
  // Financial visualizations (charts, tables) from tool execution.
  visualizations?:
    | Array<{
        type: string;
        title: string;
        data: Record<string, unknown>[];
        config: Record<string, unknown>;
      }>
    | undefined;
}

export interface ChatMessage {
  id: string;
  createdAt: string;
  role: ChatRole;
  content: string;
  meta?: ChatMessageMeta | undefined;
  // UI-side streaming indicator
  isStreaming?: boolean | undefined;
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
  category?: string;
}
