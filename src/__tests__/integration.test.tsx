import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import ProviderSelector from '../../src/components/ProviderSelector';
import ModelSelector from '../../src/components/ModelSelector';
import GoblinDemo from '../../src/components/GoblinDemo';

// Mock the runtime client
vi.mock('../../src/api/tauri-client', () => ({
  runtimeClient: {
    getGoblins: vi.fn().mockResolvedValue([
      { id: "docs-writer", name: "docs-writer", title: "Documentation Writer", status: "available" },
      { id: "code-writer", name: "code-writer", title: "Code Writer", status: "available" }
    ]),
    getProviders: vi.fn().mockResolvedValue(["openai", "anthropic", "google"]),
    getProviderModels: vi.fn().mockImplementation((provider: string) => {
      const models: Record<string, string[]> = {
        "openai": ["gpt-4", "gpt-3.5-turbo"],
        "anthropic": ["claude-3", "claude-2"],
        "google": ["gemini-pro", "gemini-pro-vision"]
      };
      return Promise.resolve(models[provider] || []);
    }),
    executeTask: vi.fn().mockResolvedValue("Executed: task completed successfully"),
    parseOrchestration: vi.fn().mockResolvedValue({
      steps: [
        { id: "step1", goblin: "docs-writer", task: "document this code", dependencies: [], batch: 0 }
      ],
      total_batches: 1,
      max_parallel: 1
    }),
    getHistory: vi.fn().mockResolvedValue([]),
    getStats: vi.fn().mockResolvedValue({}),
    getCostSummary: vi.fn().mockResolvedValue({ total_cost: 0, cost_by_provider: {}, cost_by_model: {} }),
    executeTaskStreaming: vi.fn().mockImplementation(async (_goblin: string, _task: string, onChunk: Function) => {
      onChunk({ chunk: "Executed: streaming task completed", result: true });
    }),
    executeGoblinCommand: vi.fn().mockResolvedValue({
      result: "Executed: command completed",
      status: 'success'
    })
  },
  runtimeClientDemo: {
    getGoblins: vi.fn().mockResolvedValue([
      { id: "docs-writer", name: "docs-writer", title: "Documentation Writer", status: "available" },
      { id: "code-writer", name: "code-writer", title: "Code Writer", status: "available" }
    ]),
    getProviders: vi.fn().mockResolvedValue(["openai", "anthropic", "google"]),
    getProviderModels: vi.fn().mockImplementation((provider: string) => {
      const models: Record<string, string[]> = {
        "openai": ["gpt-4", "gpt-3.5-turbo"],
        "anthropic": ["claude-3", "claude-2"],
        "google": ["gemini-pro", "gemini-pro-vision"]
      };
      return Promise.resolve(models[provider] || []);
    }),
    executeTask: vi.fn().mockResolvedValue("Executed: demo task completed successfully"),
    parseOrchestration: vi.fn().mockResolvedValue({
      steps: [
        { id: "step1", goblin: "docs-writer", task: "document this code", dependencies: [], batch: 0 }
      ],
      total_batches: 1,
      max_parallel: 1
    }),
    getHistory: vi.fn().mockResolvedValue([]),
    getStats: vi.fn().mockResolvedValue({}),
    getCostSummary: vi.fn().mockResolvedValue({ total_cost: 0, cost_by_provider: {}, cost_by_model: {} }),
    executeTaskStreaming: vi.fn().mockImplementation(async (_goblin: string, _task: string, onChunk: Function) => {
      onChunk({ chunk: "Executed: demo streaming task completed", result: true });
    }),
    executeGoblinCommand: vi.fn().mockResolvedValue({
      result: "Executed: demo command completed",
      status: 'success'
    })
  }
}));

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={createTestQueryClient()}>
    {children}
  </QueryClientProvider>
);

describe('Integration Tests - Provider/Model Selection Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should allow selecting a provider and then a model', async () => {
    const mockOnChange = vi.fn();

    render(
      <TestWrapper>
        <div>
          <ProviderSelector
            providers={['openai', 'anthropic', 'google']}
            onChange={mockOnChange}
          />
          <ModelSelector
            provider="openai"
            onChange={mockOnChange}
          />
        </div>
      </TestWrapper>
    );

    // Wait for components to render
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /provider/i })).toBeInTheDocument();
    });

    // Select OpenAI provider
    const providerSelect = screen.getByRole('combobox', { name: /provider/i });
    fireEvent.change(providerSelect, { target: { value: 'openai' } });

    // Wait for model selector to appear and load OpenAI models
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /model/i })).toBeInTheDocument();
    });

    const modelSelect = screen.getByRole('combobox', { name: /model/i });

    // Check that OpenAI models are available
    await waitFor(() => {
      const options = screen.getAllByRole('option');
      const modelOptions = options.filter(option =>
        option.textContent?.includes('gpt-4') ||
        option.textContent?.includes('gpt-3.5-turbo')
      );
      expect(modelOptions.length).toBeGreaterThan(0);
    });

    // Select GPT-4 model
    fireEvent.change(modelSelect, { target: { value: 'gpt-4' } });

    // Verify onChange was called with the selected model
    expect(mockOnChange).toHaveBeenCalledWith('gpt-4');
  });

  it('should update model options when provider changes', async () => {
    const mockOnChange = vi.fn();

    // Use a component that manages state
    const TestComponent = () => {
      const [selectedProvider, setSelectedProvider] = React.useState('anthropic');

      return (
        <div>
          <ProviderSelector
            providers={['openai', 'anthropic', 'google']}
            onChange={setSelectedProvider}
          />
          <ModelSelector
            provider={selectedProvider}
            onChange={mockOnChange}
          />
        </div>
      );
    };

    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    // Wait for components to render
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /provider/i })).toBeInTheDocument();
    });

    // Initially should have Claude models (anthropic is default)
    await waitFor(() => {
      const options = screen.getAllByRole('option');
      const claudeOptions = options.filter(option =>
        option.textContent?.includes('claude')
      );
      expect(claudeOptions.length).toBeGreaterThan(0);
    });

    // Change to OpenAI
    const providerSelect = screen.getByRole('combobox', { name: /provider/i });
    fireEvent.change(providerSelect, { target: { value: 'openai' } });

    // Wait for OpenAI models to replace Claude models
    await waitFor(() => {
      const options = screen.getAllByRole('option');
      const gptOptions = options.filter(option =>
        option.textContent?.includes('gpt')
      );
      const claudeOptions = options.filter(option =>
        option.textContent?.includes('claude')
      );
      expect(gptOptions.length).toBeGreaterThan(0);
      expect(claudeOptions.length).toBe(0);
    });
  });

  it('should handle provider selection errors gracefully', async () => {
    // Mock API failure
    const { runtimeClient } = await import('../../src/api/tauri-client');
    vi.mocked(runtimeClient.getProviderModels).mockRejectedValueOnce(new Error('Network error'));

    render(
      <TestWrapper>
        <ProviderSelector
          providers={['openai', 'anthropic', 'google']}
          onChange={vi.fn()}
        />
      </TestWrapper>
    );

    // Component should still render despite API error
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /provider/i })).toBeInTheDocument();
    });
  });
});

describe('Integration Tests - Goblin Demo Execution Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should execute goblin commands and display results', async () => {
    render(
      <TestWrapper>
        <GoblinDemo />
      </TestWrapper>
    );

    // Wait for the component to load
    await waitFor(() => {
      expect(screen.getByTestId('goblin-demo')).toBeInTheDocument();
    });

    // Find code input and orchestration input
    const codeInput = screen.getByTestId('code-input');
    const orchestrationInput = screen.getByTestId('orchestration-input');
    const runButton = screen.getByTestId('run-button');

    // Enter code and orchestration
    fireEvent.change(codeInput, { target: { value: 'function test() { return "hello"; }' } });
    fireEvent.change(orchestrationInput, { target: { value: 'docs-writer: document this code' } });

    // Execute the command
    fireEvent.click(runButton);

    // Wait for result
    await waitFor(() => {
      expect(screen.getByText(/Executed:/)).toBeInTheDocument();
    });
  });

  it('should handle command execution errors', async () => {
    // Mock API failure
    const { runtimeClient } = await import('../../src/api/tauri-client');
    vi.mocked(runtimeClient.executeGoblinCommand).mockRejectedValueOnce(new Error('Execution failed'));

    render(
      <TestWrapper>
        <GoblinDemo />
      </TestWrapper>
    );

    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByTestId('run-button')).toBeInTheDocument();
    });

    const codeInput = screen.getByTestId('code-input');
    const orchestrationInput = screen.getByTestId('orchestration-input');
    const runButton = screen.getByTestId('run-button');

    // Enter and execute command
    fireEvent.change(codeInput, { target: { value: 'function failing() { throw new Error(); }' } });
    fireEvent.change(orchestrationInput, { target: { value: 'failing command' } });
    fireEvent.click(runButton);

    // Wait for error message
    await waitFor(() => {
      expect(screen.getByText(/error|failed/i)).toBeInTheDocument();
    });
  });
});

describe('Integration Tests - Full Application Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should integrate provider selection with goblin demo execution', async () => {
    // Test component that properly connects provider and model selection
    const TestIntegration = () => {
      const [selectedProvider, setSelectedProvider] = React.useState<string>('openai');
      const [selectedModel, setSelectedModel] = React.useState<string>('gpt-4');

      return (
        <div>
          <ProviderSelector
            providers={['openai', 'anthropic', 'google']}
            selected={selectedProvider}
            onChange={setSelectedProvider}
          />
          <ModelSelector
            provider={selectedProvider}
            selected={selectedModel}
            onChange={setSelectedModel}
          />
          <GoblinDemo provider={selectedProvider} model={selectedModel} />
        </div>
      );
    };

    render(
      <TestWrapper>
        <TestIntegration />
      </TestWrapper>
    );

    // Verify initial state
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /provider/i })).toHaveValue('openai');
    });

    const providerSelect = screen.getByRole('combobox', { name: /provider/i });
    const modelSelect = screen.getByRole('combobox', { name: /model/i });

    // Change provider
    fireEvent.change(providerSelect, { target: { value: 'anthropic' } });

    await waitFor(() => {
      expect(providerSelect).toHaveValue('anthropic');
    });

    // Change model
    await waitFor(() => {
      expect(modelSelect).toBeInTheDocument();
    });

    fireEvent.change(modelSelect, { target: { value: 'claude-3' } });

    // Execute a goblin command
    const codeInput = screen.getByTestId('code-input');
    const orchestrationInput = screen.getByTestId('orchestration-input');
    const runButton = screen.getByTestId('run-button');

    fireEvent.change(codeInput, { target: { value: 'function analyze() { return "analysis"; }' } });
    fireEvent.change(orchestrationInput, { target: { value: 'analyze with gpt-4' } });
    fireEvent.click(runButton);

    // Verify the full flow worked
    await waitFor(() => {
      expect(screen.getByText(/Executed:/)).toBeInTheDocument();
    });

    expect(providerSelect).toHaveValue('anthropic');
    expect(modelSelect).toHaveValue('claude-3');
  });
});
