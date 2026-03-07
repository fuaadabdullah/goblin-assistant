import {
  initialOrchestrationState,
  orchestrationReducer,
  type OrchestrationState,
} from '../orchestrationState';

describe('orchestrationReducer', () => {
  test('sets primitive state fields', () => {
    let state = initialOrchestrationState;

    state = orchestrationReducer(state, { type: 'SET_CODE_INPUT', payload: 'const x = 1;' });
    state = orchestrationReducer(state, { type: 'SET_ORCHESTRATION', payload: 'docs-writer: test' });
    state = orchestrationReducer(state, { type: 'SET_RUNNING', payload: true });
    state = orchestrationReducer(state, { type: 'SET_IS_STREAMING', payload: true });

    expect(state.codeInput).toBe('const x = 1;');
    expect(state.orchestration).toBe('docs-writer: test');
    expect(state.running).toBe(true);
    expect(state.isStreaming).toBe(true);
  });

  test('updates streaming text with both direct and updater payloads', () => {
    let state = initialOrchestrationState;

    state = orchestrationReducer(state, { type: 'SET_STREAMING_TEXT', payload: 'chunk-1' });
    state = orchestrationReducer(state, {
      type: 'SET_STREAMING_TEXT',
      payload: prev => `${prev}\nchunk-2`,
    });

    expect(state.streamingText).toBe('chunk-1\nchunk-2');
  });

  test('tracks step status, costs, tokens, and chunks', () => {
    let state = initialOrchestrationState;

    state = orchestrationReducer(state, {
      type: 'SET_STEP_STATUS',
      payload: { stepId: 's1', status: 'running' },
    });
    state = orchestrationReducer(state, {
      type: 'SET_STEP_COST',
      payload: { stepId: 's1', cost: 0.0012 },
    });
    state = orchestrationReducer(state, {
      type: 'SET_STEP_TOKENS',
      payload: { stepId: 's1', tokens: 42 },
    });
    state = orchestrationReducer(state, {
      type: 'ADD_STEP_CHUNK',
      payload: { stepId: 's1', chunk: { chunk: 'hello', token: 42, cost: 0.0012 } },
    });

    expect(state.stepStatuses.s1).toBe('running');
    expect(state.stepCosts.s1).toBe(0.0012);
    expect(state.stepTokens.s1).toBe(42);
    expect(state.stepChunks.s1).toEqual([{ chunk: 'hello', token: 42, cost: 0.0012 }]);
  });

  test('toggles expanded step and resets execution state', () => {
    let state: OrchestrationState = {
      ...initialOrchestrationState,
      streamingText: 'existing stream',
      running: true,
      plan: { steps: [], total_batches: 1, max_parallel: 1 },
      stepStatuses: { s1: 'completed' },
      stepCosts: { s1: 0.01 },
      stepTokens: { s1: 123 },
      stepChunks: { s1: [{ chunk: 'x', token: 1, cost: 0.0001 }] },
      isStreaming: true,
      fallbackTriggered: true,
    };

    state = orchestrationReducer(state, { type: 'TOGGLE_EXPANDED_STEP', payload: 's1' });
    expect(state.expandedSteps.s1).toBe(true);

    state = orchestrationReducer(state, { type: 'TOGGLE_EXPANDED_STEP', payload: 's1' });
    expect(state.expandedSteps.s1).toBe(false);

    state = orchestrationReducer(state, { type: 'RESET_EXECUTION' });
    expect(state.streamingText).toBe('');
    expect(state.running).toBe(false);
    expect(state.plan).toBeNull();
    expect(state.stepStatuses).toEqual({});
    expect(state.stepCosts).toEqual({});
    expect(state.stepTokens).toEqual({});
    expect(state.stepChunks).toEqual({});
    expect(state.isStreaming).toBe(false);
    expect(state.fallbackTriggered).toBe(false);
  });
});
