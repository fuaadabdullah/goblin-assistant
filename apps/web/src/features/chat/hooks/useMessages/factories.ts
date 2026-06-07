import { computeCostUsd } from '../../../../lib/llm-rates';
import type { ChatMessageMeta, ChatUsage } from '../../../../domain/chat';
import type { ChatMessage } from '../../types';
import type { PendingAttachment } from '../useChatSession';

export const createMessageId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
};

export const calculateTotals = (items: ChatMessage[]) => {
  const totals = items.reduce(
    (acc, message) => {
      const usageTokens = message.meta?.usage?.total_tokens;
      const inputTokens = message.meta?.usage?.input_tokens || 0;
      const outputTokens = message.meta?.usage?.output_tokens || 0;
      const tokens = typeof usageTokens === 'number' ? usageTokens : inputTokens + outputTokens;

      if (typeof tokens === 'number' && Number.isFinite(tokens)) {
        acc.totalTokens += tokens;
      }
      if (typeof message.meta?.cost_usd === 'number' && Number.isFinite(message.meta.cost_usd)) {
        acc.totalCostUsd += message.meta.cost_usd;
      }
      return acc;
    },
    { totalTokens: 0, totalCostUsd: 0 }
  );

  return {
    totalTokens: totals.totalTokens,
    totalCostUsd: Number(totals.totalCostUsd.toFixed(6)),
  };
};

export const mapAttachments = (attachments: PendingAttachment[]) =>
  attachments.map((attachment) => ({
    id: attachment.file_id,
    filename: attachment.filename,
    mime_type: attachment.mime_type,
    size_bytes: attachment.size_bytes,
  }));

export const createAssistantMessage = (response: {
  messageId?: string;
  createdAt?: string;
  content?: string;
  provider?: string;
  model?: string;
  usage?: ChatUsage;
  cost_usd?: number;
  correlation_id?: string;
  visualizations?: ChatMessageMeta['visualizations'];
}): ChatMessage => {
  const rawCost = typeof response.cost_usd === 'number' ? response.cost_usd : undefined;
  const resolvedCost =
    rawCost !== undefined
      ? { cost_usd: rawCost, approx: false }
      : computeCostUsd(response.usage, response.provider, response.model);

  return {
    id: response.messageId || createMessageId(),
    createdAt: response.createdAt || new Date().toISOString(),
    role: 'assistant',
    content: response.content || 'No response',
    meta: {
      provider: response.provider,
      model: response.model,
      usage: response.usage,
      cost_usd: resolvedCost.cost_usd,
      cost_is_approx: resolvedCost.approx,
      correlation_id: response.correlation_id,
      visualizations: response.visualizations,
    },
  };
};
