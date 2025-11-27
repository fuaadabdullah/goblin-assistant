import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import GoblinDemo from '@/pages/GoblinDemo';
import type { StreamChunk, TaskResponse } from '@/api/api-client';

// Mock the runtimeClient
vi.mock('@/api/api-client', () => {
  return {
    runtimeClient: {
      parseOrchestration: vi.fn(),
      executeTaskStreaming: vi.fn(),
      executeTask: vi.fn(),
    },
    runtimeClientDemo: {
      parseOrchestration: vi.fn(),
      executeTaskStreaming: vi.fn(),
      executeTask: vi.fn(),
    },
  };
});

import { runtimeClient, runtimeClientDemo } from '@/api/api-client';

const mockParseOrchestration = vi.mocked(runtimeClient.parseOrchestration);
const mockExecuteTaskStreaming = vi.mocked(runtimeClient.executeTaskStreaming);
const mockExecuteTask = vi.mocked(runtimeClient.executeTask);
const mockDemoParseOrchestration = vi.mocked(runtimeClientDemo.parseOrchestration);
const mockDemoExecuteTaskStreaming = vi.mocked(runtimeClientDemo.executeTaskStreaming);
const mockDemoExecuteTask = vi.mocked(runtimeClientDemo.executeTask);

describe('GoblinDemo', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset all mocks to default implementations
    mockParseOrchestration.mockResolvedValue({
      steps: [
        {
          id: 'step1',
          goblin: 'docs-writer',
          task: 'document this code',
          dependencies: [],
          batch: 0,
        },
        {
          id: 'step2',
          goblin: 'code-writer',
          task: 'write a unit test',
          dependencies: ['step1'],
          batch: 1,
        },
      ],
      total_batches: 1,
      max_parallel: 1,
    });
    mockExecuteTaskStreaming.mockImplementation(
      async (
        _goblin: string,
        _task: string,
        onChunk: (chunk: StreamChunk) => void,
        onComplete?: (result: TaskResponse) => void
      ) => {
        // Simulate async streaming with cost
        await new Promise(resolve => setTimeout(resolve, 10)); // Small delay
        onChunk({ chunk: 'Starting...', token_count: 10, cost_delta: 0.0005 });
        onChunk({ chunk: 'Processing...', token_count: 20, cost_delta: 0.0005 });
        if (onComplete) {
          onComplete({
            cost: 0.001,
            reasoning: 'Completed task',
          });
        }
      }
    );
    mockExecuteTask.mockResolvedValue('Fallback result');
    mockDemoParseOrchestration.mockResolvedValue({
      steps: [
        {
          id: 'step1',
          goblin: 'docs-writer',
          task: 'document this code',
          dependencies: [],
          batch: 0,
        },
      ],
      total_batches: 1,
      max_parallel: 1,
    });
    mockDemoExecuteTaskStreaming.mockImplementation(
      async (
        _goblin: string,
        _task: string,
        onChunk: (chunk: StreamChunk) => void,
        onComplete?: (result: TaskResponse) => void
      ) => {
        // Simulate async streaming with cost for demo
        await new Promise(resolve => setTimeout(resolve, 10)); // Small delay
        onChunk({ chunk: 'Demo starting...' });
        if (onComplete) {
          onComplete({
            cost: 0.001,
            reasoning: 'Demo completed',
          });
        }
      }
    );
    mockDemoExecuteTask.mockResolvedValue('Demo fallback result');
  });

  it('renders with default props', () => {
    render(<GoblinDemo />);

    expect(screen.getByTestId('goblin-demo')).toBeInTheDocument();
    expect(screen.getByTestId('goblin-inputs')).toBeInTheDocument();
    expect(screen.getByTestId('code-input')).toBeInTheDocument();
    expect(screen.getByTestId('template-select')).toBeInTheDocument();
    expect(screen.getByTestId('orchestration-input')).toBeInTheDocument();
    expect(screen.getByTestId('run-button')).toBeInTheDocument();
  });

  it('displays default code input', () => {
    render(<GoblinDemo />);

    const codeInput = screen.getByTestId('code-input');
    expect(codeInput).toHaveValue(
      '// Write code or paste here\nfunction add(a, b) {\n  return a + b;\n}'
    );
  });

  it('displays default orchestration input', () => {
    render(<GoblinDemo />);

    const orchInput = screen.getByTestId('orchestration-input');
    expect(orchInput).toHaveValue(
      'docs-writer: document this code THEN code-writer: write a unit test'
    );
  });

  it('shows all orchestration templates', () => {
    render(<GoblinDemo />);

    expect(screen.getByTestId('template-option-document-&-test')).toBeInTheDocument();
    expect(screen.getByTestId('template-option-analyze-&-optimize')).toBeInTheDocument();
    expect(screen.getByTestId('template-option-review-&-refactor')).toBeInTheDocument();
    expect(screen.getByTestId('template-option-custom')).toBeInTheDocument();
  });

  it('changes orchestration when template is selected', () => {
    render(<GoblinDemo />);

    const templateSelect = screen.getByTestId('template-select');
    fireEvent.change(templateSelect, { target: { value: 'Analyze & Optimize' } });

    const orchInput = screen.getByTestId('orchestration-input');
    expect(orchInput).toHaveValue(
      'code-writer: analyze this code for issues THEN code-writer: suggest optimizations'
    );
  });

  it('allows custom orchestration input', async () => {
    render(<GoblinDemo />);

    // Initially should have default orchestration
    const orchInput = screen.getByTestId('orchestration-input');
    expect(orchInput).toHaveValue(
      'docs-writer: document this code THEN code-writer: write a unit test'
    );

    const templateSelect = screen.getByTestId('template-select');

    await act(async () => {
      fireEvent.change(templateSelect, { target: { value: 'Custom' } });
    });

    await waitFor(() => {
      expect(orchInput).toHaveValue('');
    });

    await act(async () => {
      fireEvent.change(orchInput, { target: { value: 'custom: do something' } });
    });
    expect(orchInput).toHaveValue('custom: do something');
  });
  it('updates code input when changed', () => {
    render(<GoblinDemo />);

    const codeInput = screen.getByTestId('code-input');
    const newCode = 'function multiply(a, b) { return a * b; }';

    fireEvent.change(codeInput, { target: { value: newCode } });
    expect(codeInput).toHaveValue(newCode);
  });

  it('previews orchestration plan when orchestration changes', async () => {
    render(<GoblinDemo />);

    await waitFor(() => {
      expect(mockParseOrchestration).toHaveBeenCalledWith(
        'docs-writer: document this code THEN code-writer: write a unit test',
        expect.any(String)
      );
    });

    // Wait for the plan preview to be rendered after the async call completes
    await waitFor(() => {
      expect(screen.getByTestId('plan-preview')).toBeInTheDocument();
    });

    expect(screen.getByTestId('plan-preview-title')).toHaveTextContent('Plan Preview (2 steps)');
    expect(screen.getByTestId('estimated-cost')).toHaveTextContent('Estimated Cost: $0.0400');
  });

  it('shows plan steps in preview', async () => {
    render(<GoblinDemo />);

    await waitFor(() => {
      expect(screen.getByTestId('plan-steps')).toBeInTheDocument();
    });

    expect(screen.getByTestId('plan-step-step1')).toBeInTheDocument();
    expect(screen.getByTestId('step-goblin-step1')).toHaveTextContent('docs-writer:');
    expect(screen.getByTestId('step-task-step1')).toHaveTextContent('document this code');
  });

  it('clears preview when orchestration is empty', async () => {
    render(<GoblinDemo />);

    // Wait for initial preview
    await waitFor(() => {
      expect(screen.getByTestId('plan-preview')).toBeInTheDocument();
    });

    // Clear orchestration directly
    const orchInput = screen.getByTestId('orchestration-input');
    await act(async () => {
      fireEvent.change(orchInput, { target: { value: '' } });
    });

    await waitFor(() => {
      expect(screen.queryByTestId('plan-preview')).not.toBeInTheDocument();
    });
  });

  it('parses orchestration and executes steps with cost updates', async () => {
    render(<GoblinDemo provider="openai" />);

    // Set orchestration input
    const orchInput = screen.getByTestId('orchestration-input');
    fireEvent.change(orchInput, {
      target: { value: 'docs-writer: document this code THEN code-writer: write a unit test' },
    });

    // Click run
    const runButton = screen.getByTestId('run-button');
    fireEvent.click(runButton);

    // Wait for parse to be called
    await waitFor(() => {
      expect(mockParseOrchestration).toHaveBeenCalledWith(
        'docs-writer: document this code THEN code-writer: write a unit test',
        expect.any(String)
      );
    });

    // Wait for execution
    await waitFor(() => {
      expect(mockExecuteTaskStreaming).toHaveBeenCalledTimes(2);
    });

    // Check that plan is shown
    await waitFor(() => {
      expect(screen.getByTestId('execution-plan')).toBeInTheDocument();
    });

    // Check total cost is displayed
    await waitFor(() => {
      expect(screen.getByTestId('plan-total')).toBeInTheDocument();
    });
  });

  it('disables run button while running', async () => {
    // Make execution take longer
    mockExecuteTaskStreaming.mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    render(<GoblinDemo />);

    const runButton = screen.getByTestId('run-button');
    fireEvent.click(runButton);

    // Button should be disabled immediately
    expect(runButton).toBeDisabled();
    expect(runButton).toHaveTextContent('Running...');

    // Wait for completion
    await waitFor(() => {
      expect(runButton).not.toBeDisabled();
    });
    expect(runButton).toHaveTextContent('Run');
  });

  it('expands and collapses step details', async () => {
    render(<GoblinDemo />);

    // Run orchestration
    const runButton = screen.getByTestId('run-button');
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.getByTestId('execution-step-step1')).toBeInTheDocument();
    });

    // Initially not expanded
    expect(screen.queryByTestId('step-details-step1')).not.toBeInTheDocument();

    // Click to expand
    const stepElement = screen.getByTestId('execution-step-step1');
    fireEvent.click(stepElement);

    await waitFor(() => {
      expect(screen.getByTestId('step-details-step1')).toBeInTheDocument();
    });

    // Click again to collapse
    fireEvent.click(stepElement);

    await waitFor(() => {
      expect(screen.queryByTestId('step-details-step1')).not.toBeInTheDocument();
    });
  });

  it('shows step status and cost information', async () => {
    render(<GoblinDemo />);

    // Run orchestration
    const runButton = screen.getByTestId('run-button');
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.getByTestId('execution-step-step1')).toBeInTheDocument();
    });

    // Wait for execution to complete (mock has 10ms delay)
    await waitFor(() => {
      expect(screen.getByTestId('execution-step-status-step1')).toHaveTextContent('(completed)');
    });

    // Check cost is displayed
    expect(screen.getByTestId('execution-step-cost-step1')).toHaveTextContent('$0.001000');
  });

  it('handles demo mode correctly', async () => {
    render(<GoblinDemo demoMode={true} />);

    // Run orchestration
    const runButton = screen.getByTestId('run-button');
    fireEvent.click(runButton);

    // Should use demo client
    await waitFor(() => {
      expect(mockDemoParseOrchestration).toHaveBeenCalled();
      expect(mockDemoExecuteTaskStreaming).toHaveBeenCalled();
    });
  });

  it('handles parsing errors gracefully', async () => {
    mockParseOrchestration.mockRejectedValue(new Error('Parse failed'));

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(<GoblinDemo />);

    // Run orchestration
    const runButton = screen.getByTestId('run-button');
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        '❌ [DEBUG] Failed to preview orchestration:',
        expect.any(Error)
      );
    });

    consoleSpy.mockRestore();
  });

  it('handles execution errors with fallback', async () => {
    mockExecuteTaskStreaming.mockRejectedValue(new Error('Streaming failed'));

    render(<GoblinDemo />);

    // Run orchestration
    const runButton = screen.getByTestId('run-button');
    fireEvent.click(runButton);

    // Should eventually call fallback
    await waitFor(() => {
      expect(mockExecuteTask).toHaveBeenCalled();
    });
  });

  it('shows streaming output during execution', async () => {
    render(<GoblinDemo />);

    // Run orchestration
    const runButton = screen.getByTestId('run-button');
    fireEvent.click(runButton);

    // Check streaming view appears
    await waitFor(() => {
      expect(screen.getByTestId('streaming-view')).toBeInTheDocument();
    });

    expect(screen.getByTestId('streaming-title')).toHaveTextContent('Streaming Output');
  });

  it('displays chunk information when step is expanded', async () => {
    render(<GoblinDemo />);

    // Run orchestration
    const runButton = screen.getByTestId('run-button');
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.getByTestId('execution-step-step1')).toBeInTheDocument();
    });

    // Wait for execution to complete and chunks to be available
    await waitFor(() => {
      expect(screen.getByTestId('execution-step-status-step1')).toHaveTextContent('(completed)');
    });

    // Expand step
    const stepElement = screen.getByTestId('execution-step-step1');
    fireEvent.click(stepElement);

    await waitFor(() => {
      expect(screen.getByTestId('step-details-step1')).toBeInTheDocument();
    });

    // Wait for chunk list to be rendered
    await waitFor(() => {
      expect(screen.getByTestId('chunk-list-step1')).toBeInTheDocument();
    });

    // Check chunk information is displayed
    expect(screen.getByTestId('chunks-step1')).toBeInTheDocument();
    expect(screen.getByTestId('chunk-step1-0')).toBeInTheDocument();
    expect(screen.getByTestId('chunk-text-step1-0')).toHaveTextContent('Starting...');
  });

  it('passes provider and model to execution', async () => {
    render(<GoblinDemo provider="openai" model="gpt-4" />);

    // Run orchestration
    const runButton = screen.getByTestId('run-button');
    fireEvent.click(runButton);

    // Check that provider and model are passed to execution
    await waitFor(() => {
      expect(mockExecuteTaskStreaming).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
        expect.any(Function),
        expect.any(Function),
        expect.any(String), // codeInput
        'openai', // provider
        'gpt-4' // model
      );
    });
  });
});
