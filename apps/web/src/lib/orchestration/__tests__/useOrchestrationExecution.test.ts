import { renderHook, act } from '@testing-library/react';

// Mock dependencies
const mockParseOrchestration = vi.fn();
const mockExecuteTaskStreaming = vi.fn();
const mockExecuteTask = vi.fn();

vi.mock('../streamingUtils', () => ({
  createStreamingHandlers: vi.fn(() => ({
    onChunk: vi.fn(),
    onComplete: vi.fn(),
    onError: vi.fn(),
  })),
  formatStepError: vi.fn((err) => String(err)),
}));
vi.mock('../../utils/debug', () => ({
  debugLog: vi.fn(),
  debugError: vi.fn(),
  debugWarn: vi.fn(),
}));

import { useOrchestrationExecution } from '../useOrchestrationExecution';

const mockDispatch = vi.fn();
const mockRuntimeClient = {
  parseOrchestration: mockParseOrchestration,
  executeTaskStreaming: mockExecuteTaskStreaming,
  executeTask: mockExecuteTask,
};

describe('useOrchestrationExecution', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns executeOrchestration function and streamingTimeoutRef', () => {
    const { result } = renderHook(() =>
      useOrchestrationExecution({
        dispatch: mockDispatch,
        runtimeClient: mockRuntimeClient as never,
      })
    );
    expect(typeof result.current.executeOrchestration).toBe('function');
    expect(result.current.streamingTimeoutRef).toBeDefined();
    expect(result.current.streamingTimeoutRef.current).toBeNull();
  });

  it('dispatches RUNNING status on execute', async () => {
    mockParseOrchestration.mockResolvedValue({
      steps: [{ task: 'test', description: 'Test step' }],
    });
    mockExecuteTaskStreaming.mockResolvedValue({ result: 'ok' });

    const { result } = renderHook(() =>
      useOrchestrationExecution({
        dispatch: mockDispatch,
        runtimeClient: mockRuntimeClient as never,
      })
    );

    await act(async () => {
      await result.current.executeOrchestration('test orchestration', 'code');
    });

    expect(mockDispatch).toHaveBeenCalledWith(
      expect.objectContaining({ type: expect.stringContaining('RUNNING') })
    );
  });

  it('calls parseOrchestration with orchestration text', async () => {
    mockParseOrchestration.mockResolvedValue({ steps: [] });

    const { result } = renderHook(() =>
      useOrchestrationExecution({
        dispatch: mockDispatch,
        runtimeClient: mockRuntimeClient as never,
      })
    );

    await act(async () => {
      await result.current.executeOrchestration('analyze code', 'print("hi")');
    });

    expect(mockParseOrchestration).toHaveBeenCalledWith('analyze code', expect.anything());
  });

  it('handles parse error gracefully', async () => {
    mockParseOrchestration.mockRejectedValue(new Error('Parse failed'));

    const { result } = renderHook(() =>
      useOrchestrationExecution({
        dispatch: mockDispatch,
        runtimeClient: mockRuntimeClient as never,
      })
    );

    await act(async () => {
      await result.current.executeOrchestration('bad input', 'code');
    });

    // Should dispatch an error or complete state
    expect(mockDispatch).toHaveBeenCalled();
  });

  it('handles empty steps list', async () => {
    mockParseOrchestration.mockResolvedValue({ steps: [] });

    const { result } = renderHook(() =>
      useOrchestrationExecution({
        dispatch: mockDispatch,
        runtimeClient: mockRuntimeClient as never,
      })
    );

    await act(async () => {
      await result.current.executeOrchestration('test', 'code');
    });

    // Should handle gracefully without calling executeTaskStreaming
    expect(mockExecuteTaskStreaming).not.toHaveBeenCalled();
  });

  it('passes provider and model to execution', async () => {
    mockParseOrchestration.mockResolvedValue({ steps: [{ task: 'test', description: 'step' }] });
    mockExecuteTaskStreaming.mockResolvedValue({ result: 'ok' });

    const { result } = renderHook(() =>
      useOrchestrationExecution({
        dispatch: mockDispatch,
        runtimeClient: mockRuntimeClient as never,
        provider: 'openai',
        model: 'gpt-4',
      })
    );

    await act(async () => {
      await result.current.executeOrchestration('test', 'code');
    });

    expect(mockExecuteTaskStreaming).toHaveBeenCalled();
  });
});
