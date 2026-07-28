import { useCallback, useEffect, useState } from 'react';
import { chatClient } from '../api';
import { estimateFromText, type TextCostEstimate } from '../../../lib/cost-estimate';
import { devWarn } from '@/utils/dev-log';

export interface InputEstimatesState {
  localInputEstimate: TextCostEstimate | null;
  serverInputEstimate: TextCostEstimate | null;
  inputEstimate: TextCostEstimate | null;
}

export interface InputEstimatesProps {
  input: string;
  conversationId?: string | null | undefined;
  selectedProvider?: string | undefined;
  selectedModel?: string | undefined;
}

/**
 * Manages token and cost estimation for chat input
 * Uses local heuristic for quick feedback and server-side estimate for accuracy
 */
export const useInputEstimates = ({
  input,
  conversationId,
  selectedProvider,
  selectedModel,
}: InputEstimatesProps): InputEstimatesState => {
  const [serverInputEstimate, setServerInputEstimate] = useState<TextCostEstimate | null>(null);

  // Client-side estimate: quick but less accurate
  const localInputEstimate =
    input.length > 0
      ? (() => {
          const est = estimateFromText(input);
          return est.estimated_tokens > 0 ? est : null;
        })()
      : null;

  // Server-side estimate: more accurate but only for longer inputs
  useEffect(() => {
    if (input.length <= 200) {
      setServerInputEstimate(null);
      return;
    }

    let cancelled = false;
    const handle = setTimeout(() => {
      chatClient
        .estimateTokens({
          message: input,
          conversationId: conversationId ?? undefined,
          provider: selectedProvider,
          model: selectedModel,
        })
        .then((est) => {
          if (cancelled) return;
          setServerInputEstimate({
            estimated_tokens: est.input_tokens + est.estimated_output_tokens,
            estimated_cost_usd: est.estimated_cost_usd,
          });
        })
        .catch((err) => {
          if (cancelled) return;
          devWarn('chat.estimate_tokens_failed', { error: String(err) });
          setServerInputEstimate(null);
        });
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [input, conversationId, selectedProvider, selectedModel]);

  // Prefer server estimate (more accurate) over local estimate
  const inputEstimate = serverInputEstimate ?? localInputEstimate;

  return {
    localInputEstimate,
    serverInputEstimate,
    inputEstimate,
  };
};
