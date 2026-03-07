/**
 * Streaming utilities for orchestration execution
 */

import type { StreamChunk, TaskResponse } from '@/types/api';
import type { OrchestrationAction } from '@/lib/orchestration/orchestrationState';
import { debugLog } from '@/lib/utils/debug';

export interface StreamingHandlers {
  onChunk: (chunk: StreamChunk) => void;
  onComplete: (final: TaskResponse) => void;
}

/**
 * Create streaming handlers for orchestration step execution
 */
export function createStreamingHandlers(
  stepId: string,
  dispatch: React.Dispatch<OrchestrationAction>,
  clearTimeoutFn?: () => void
): StreamingHandlers {
  return {
    onChunk: (chunk: StreamChunk) => {
      debugLog('📦 [DEBUG] Received chunk:', {
        stepId,
        chunkPreview: (chunk.content || JSON.stringify(chunk)).substring(0, 50) + '...',
        tokenCount: chunk.token_count,
        costDelta: chunk.cost_delta,
      });

      // Clear timeout on first chunk received
      if (clearTimeoutFn) {
        clearTimeoutFn();
      }

      const chunkText = chunk.content || JSON.stringify(chunk);
      dispatch({
        type: 'SET_STREAMING_TEXT',
        payload: (s: string) => s + chunkText + '\n',
      });

      const tokenCount = (chunk.token_count as number) || (chunk.tokenCount as number) || 0;
      const costDelta = (chunk.cost_delta as number) || (chunk.costDelta as number) || 0;

      if (tokenCount) {
        dispatch({
          type: 'SET_STEP_TOKENS',
          payload: { stepId, tokens: tokenCount },
        });
      }

      if (tokenCount || costDelta) {
        dispatch({
          type: 'ADD_STEP_CHUNK',
          payload: {
            stepId,
            chunk: { chunk: chunkText, token: tokenCount, cost: costDelta },
          },
        });
      }
    },

    onComplete: (final: TaskResponse) => {
      debugLog('🏁 [DEBUG] Step completed:', {
        stepId,
        cost: (final as Record<string, unknown>)?.cost,
        reasoning:
          String((final as Record<string, unknown>)?.reasoning || '').substring(0, 50) + '...',
      });

      dispatch({
        type: 'SET_STREAMING_TEXT',
        payload: (s: string) =>
          s + `--- Step ${stepId} COMPLETE ---\n` + JSON.stringify(final) + '\n',
      });

      const cost = Number((final as Record<string, unknown>)?.cost) || 0;
      dispatch({
        type: 'SET_STEP_COST',
        payload: { stepId, cost },
      });
    },
  };
}

/**
 * Extract token count and cost delta from a StreamChunk
 */
export function extractChunkMetrics(chunk: StreamChunk): { tokens: number; cost: number } {
  const tokens = (chunk.token_count as number) || (chunk.tokenCount as number) || 0;
  const cost = (chunk.cost_delta as number) || (chunk.costDelta as number) || 0;
  return { tokens, cost };
}

/**
 * Format step completion message
 */
export function formatStepCompletion(stepId: string, final: TaskResponse): string {
  return `--- Step ${stepId} COMPLETE ---\n${JSON.stringify(final)}\n`;
}

/**
 * Format step error message
 */
export function formatStepError(stepId: string, error: unknown): string {
  const errorMessage = error instanceof Error ? error.message : String(error);
  return `--- Step ${stepId} FAILED ---\nError: ${errorMessage}\n`;
}
