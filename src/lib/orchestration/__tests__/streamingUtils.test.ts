import {
  createStreamingHandlers,
  extractChunkMetrics,
  formatStepCompletion,
  formatStepError,
} from '../streamingUtils';
import type { OrchestrationAction } from '../orchestrationState';
import type { StreamChunk, TaskResponse } from '../../../types/api';

describe('streamingUtils', () => {
  test('extractChunkMetrics supports snake_case and camelCase', () => {
    const snakeChunk = {
      content: 'hello',
      token_count: 10,
      cost_delta: 0.0002,
    } as StreamChunk;

    const camelChunk = {
      content: 'world',
      tokenCount: 20,
      costDelta: 0.0004,
    } as StreamChunk;

    expect(extractChunkMetrics(snakeChunk)).toEqual({ tokens: 10, cost: 0.0002 });
    expect(extractChunkMetrics(camelChunk)).toEqual({ tokens: 20, cost: 0.0004 });
  });

  test('createStreamingHandlers dispatches expected actions for chunk + completion', () => {
    const dispatch = jest.fn<void, [OrchestrationAction]>();
    const clearTimeoutFn = jest.fn();
    const handlers = createStreamingHandlers('s1', dispatch, clearTimeoutFn);

    const chunk = {
      content: 'chunk-data',
      token_count: 12,
      cost_delta: 0.001,
    } as StreamChunk;

    handlers.onChunk(chunk);

    expect(clearTimeoutFn).toHaveBeenCalledTimes(1);
    expect(dispatch).toHaveBeenCalledWith({
      type: 'SET_STREAMING_TEXT',
      payload: expect.any(Function),
    });
    expect(dispatch).toHaveBeenCalledWith({
      type: 'SET_STEP_TOKENS',
      payload: { stepId: 's1', tokens: 12 },
    });
    expect(dispatch).toHaveBeenCalledWith({
      type: 'ADD_STEP_CHUNK',
      payload: {
        stepId: 's1',
        chunk: { chunk: 'chunk-data', token: 12, cost: 0.001 },
      },
    });

    const final = {
      result: { text: 'done' },
      cost: 0.0042,
      reasoning: 'completed',
    } as unknown as TaskResponse;

    handlers.onComplete(final);

    expect(dispatch).toHaveBeenCalledWith({
      type: 'SET_STREAMING_TEXT',
      payload: expect.any(Function),
    });
    expect(dispatch).toHaveBeenCalledWith({
      type: 'SET_STEP_COST',
      payload: { stepId: 's1', cost: 0.0042 },
    });
  });

  test('format helpers produce stable output', () => {
    const completion = formatStepCompletion('s2', { result: { ok: true } } as unknown as TaskResponse);
    expect(completion).toContain('--- Step s2 COMPLETE ---');

    const error = formatStepError('s3', new Error('boom'));
    expect(error).toBe('--- Step s3 FAILED ---\nError: boom\n');
  });
});
