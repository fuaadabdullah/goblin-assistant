/**
 * Custom hook for orchestration execution logic
 */

import { useRef, useCallback } from 'react';
import type { OrchestrationAction } from '@/lib/orchestration/orchestrationState';
import type { RuntimeClient } from '@/types/api';
import { createStreamingHandlers, formatStepError } from './streamingUtils';
import { debugError, debugLog, debugWarn } from '@/lib/utils/debug';

export interface UseOrchestrationExecutionOptions {
  dispatch: React.Dispatch<OrchestrationAction>;
  runtimeClient: RuntimeClient;
  provider?: string | null;
  model?: string | null;
}

export interface UseOrchestrationExecutionReturn {
  executeOrchestration: (orchestration: string, codeInput: string) => Promise<void>;
  streamingTimeoutRef: React.MutableRefObject<ReturnType<typeof setTimeout> | null>;
}

/* eslint-disable max-lines-per-function, complexity */
export function useOrchestrationExecution({
  dispatch,
  runtimeClient,
  provider,
  model,
}: UseOrchestrationExecutionOptions): UseOrchestrationExecutionReturn {
  const streamingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearStreamingTimeout = useCallback(() => {
    if (streamingTimeoutRef.current) {
      clearTimeout(streamingTimeoutRef.current);
      streamingTimeoutRef.current = null;
    }
  }, []);

  const fallbackToNonStreaming = useCallback(
    async (orchestration: string, codeInput: string) => {
      try {
        dispatch({
          type: 'SET_STREAMING_TEXT',
          payload: (s: string) => s + '\n--- FALLING BACK TO NON-STREAMING MODE ---\n',
        });

        const result = await runtimeClient.executeTask(
          'docs-writer',
          orchestration,
          false,
          codeInput,
          provider || undefined,
          model || undefined
        );

        dispatch({
          type: 'SET_STREAMING_TEXT',
          payload: (s: string) => s + `Fallback result: ${result}\n`,
        });
      } catch (fallbackError: unknown) {
        dispatch({
          type: 'SET_STREAMING_TEXT',
          payload: (s: string) =>
            s +
            `Fallback also failed: ${fallbackError instanceof Error ? fallbackError.message : String(fallbackError)}\n`,
        });
      }
    },
    [dispatch, runtimeClient, provider, model]
  );

  const executeOrchestration = useCallback(
    async (orchestration: string, codeInput: string) => {
      debugLog('🚀 [DEBUG] Starting execution:', {
        orchestration,
        codeLength: codeInput.length,
      });

      dispatch({ type: 'RESET_EXECUTION' });
      dispatch({ type: 'SET_RUNNING', payload: true });
      dispatch({ type: 'SET_IS_STREAMING', payload: true });
      dispatch({ type: 'SET_FALLBACK_TRIGGERED', payload: false });

      // Set up streaming timeout for fallback (10 seconds)
      const timeout = setTimeout(() => {
        debugWarn('⏰ [DEBUG] Streaming timeout - falling back to non-streaming mode');
        dispatch({ type: 'SET_FALLBACK_TRIGGERED', payload: true });
        dispatch({ type: 'SET_IS_STREAMING', payload: false });
        fallbackToNonStreaming(orchestration, codeInput);
      }, 10000);

      streamingTimeoutRef.current = timeout;

      const goblin = 'demo';

      try {
        debugLog('🔄 [DEBUG] Parsing orchestration...');
        const parsed = await runtimeClient.parseOrchestration(orchestration, goblin);
        debugLog('✅ [DEBUG] Orchestration parsed:', {
          steps: parsed.steps?.length || 0,
          totalBatches: parsed.total_batches,
        });

        dispatch({ type: 'SET_PLAN', payload: parsed });

        if (!parsed?.steps || parsed.steps.length === 0) {
          debugWarn('⚠️ [DEBUG] No steps to run');
          dispatch({
            type: 'SET_STREAMING_TEXT',
            payload: (s: string) => s + 'No steps to run\n',
          });
          dispatch({ type: 'SET_RUNNING', payload: false });
          dispatch({ type: 'SET_IS_STREAMING', payload: false });
          return;
        }

        for (const step of parsed.steps) {
          debugLog('🎬 [DEBUG] Executing step:', {
            id: step.id,
            goblin: step.goblin,
            task: step.task.substring(0, 50) + '...',
          });

          dispatch({
            type: 'SET_STEP_STATUS',
            payload: { stepId: step.id, status: 'running' },
          });

          try {
            debugLog('📡 [DEBUG] Starting streaming execution for step:', step.id);

            const handlers = createStreamingHandlers(step.id, dispatch, clearStreamingTimeout);

            await runtimeClient.executeTaskStreaming(
              step.goblin,
              step.task,
              handlers.onChunk,
              handlers.onComplete,
              codeInput,
              provider || undefined,
              model || undefined
            );

            dispatch({
              type: 'SET_STEP_STATUS',
              payload: { stepId: step.id, status: 'completed' },
            });
          } catch (stepError: unknown) {
            debugError(`Step ${step.id} failed:`, stepError);
            dispatch({
              type: 'SET_STREAMING_TEXT',
              payload: (s: string) => s + formatStepError(step.id, stepError),
            });

            // If streaming fails, try fallback for this step
            const fallbackTriggered = false; // Get from state if needed
            if (!fallbackTriggered) {
              dispatch({ type: 'SET_FALLBACK_TRIGGERED', payload: true });
              dispatch({ type: 'SET_IS_STREAMING', payload: false });
              await fallbackToNonStreaming(orchestration, codeInput);
              break;
            }

            dispatch({
              type: 'SET_STEP_STATUS',
              payload: { stepId: step.id, status: 'failed' },
            });
          }
        }
      } catch (err: unknown) {
        debugError('Orchestration failed:', err);
        dispatch({
          type: 'SET_STREAMING_TEXT',
          payload: (s: string) =>
            s + `Error: ${err instanceof Error ? err.message : String(err)}\n`,
        });

        // If parsing fails, try non-streaming fallback
        const fallbackTriggered = false; // Get from state if needed
        if (!fallbackTriggered) {
          dispatch({ type: 'SET_FALLBACK_TRIGGERED', payload: true });
          dispatch({ type: 'SET_IS_STREAMING', payload: false });
          await fallbackToNonStreaming(orchestration, codeInput);
        }
      } finally {
        dispatch({ type: 'SET_RUNNING', payload: false });
        dispatch({ type: 'SET_IS_STREAMING', payload: false });
        clearStreamingTimeout();
      }
    },
    [dispatch, runtimeClient, provider, model, clearStreamingTimeout, fallbackToNonStreaming]
  );

  return {
    executeOrchestration,
    streamingTimeoutRef,
  };
}
/* eslint-enable max-lines-per-function, complexity */
