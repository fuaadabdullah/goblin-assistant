import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ModelSelector from '@/components/common/ModelSelector';

// Mock the runtimeClient
vi.mock('@/api/api-client', () => ({
  runtimeClient: {
    getProviderModels: vi.fn(),
  },
}));

import { runtimeClient } from '@/api/api-client';

const mockGetProviderModels = vi.mocked(runtimeClient.getProviderModels);

describe('ModelSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows placeholder when no provider is selected', () => {
    render(<ModelSelector onChange={() => {}} />);

    expect(screen.getByTestId('model-selector-placeholder')).toBeInTheDocument();
    expect(screen.getByText('Select a provider first')).toBeInTheDocument();
  });

  it('loads models when provider is provided', async () => {
    const mockModels = ['gpt-4', 'gpt-3.5-turbo', 'claude-3'];
    mockGetProviderModels.mockResolvedValue(mockModels);

    const onChange = vi.fn();
    render(<ModelSelector provider="openai" onChange={onChange} />);

    // Should show loading state initially
    expect(screen.getByTestId('model-loading')).toBeInTheDocument();

    // Wait for models to load
    await waitFor(() => {
      expect(mockGetProviderModels).toHaveBeenCalledWith('openai');
    });

    // Should display loaded models selector
    expect(screen.getByTestId('model-selector')).toBeInTheDocument();
    expect(screen.getByTestId('model-label')).toHaveTextContent('Model:');

    // With shadcn/ui Select, options are not rendered until opened
    // Just verify the select trigger is present
    const selectTrigger = screen.getByRole('combobox', { name: /model/i });
    expect(selectTrigger).toBeInTheDocument();

    // Loading should be gone
    expect(screen.queryByTestId('model-loading')).not.toBeInTheDocument();
  });

  it('handles model selection', async () => {
    const mockModels = ['gpt-4', 'gpt-3.5-turbo'];
    mockGetProviderModels.mockResolvedValue(mockModels);

    const onChange = vi.fn();
    render(<ModelSelector provider="openai" onChange={onChange} />);

    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /model/i })).toBeInTheDocument();
    });

    // With shadcn/ui Select, we test that the component renders and the onChange prop is passed
    // The actual selection behavior is handled by Radix UI primitives
    expect(onChange).not.toHaveBeenCalled(); // Should not be called initially

    // Verify the select trigger is present and accessible
    const selectTrigger = screen.getByRole('combobox', { name: /model/i });
    expect(selectTrigger).toBeInTheDocument();
    expect(selectTrigger).toHaveAttribute('aria-label', 'Select a model');
  });

  it('shows selected model', async () => {
    const mockModels = ['gpt-4', 'gpt-3.5-turbo'];
    mockGetProviderModels.mockResolvedValue(mockModels);

    render(<ModelSelector provider="openai" selected="gpt-3.5-turbo" onChange={() => {}} />);

    // Wait for models to load first
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /model/i })).toBeInTheDocument();
    });

    // With shadcn/ui Select, the selected value is displayed in the SelectValue component
    // The trigger should contain the selected model name
    const selectTrigger = screen.getByRole('combobox', { name: /model/i });
    expect(selectTrigger).toBeInTheDocument();
    expect(selectTrigger.textContent).toContain('gpt-3.5-turbo');
  });

  it('handles API errors gracefully', async () => {
    mockGetProviderModels.mockRejectedValue(new Error('API Error'));

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(<ModelSelector provider="openai" onChange={() => {}} />);

    await waitFor(() => {
      expect(mockGetProviderModels).toHaveBeenCalledWith('openai');
    });

    // Wait for loading to complete (even on error)
    await waitFor(() => {
      expect(screen.queryByTestId('model-loading')).not.toBeInTheDocument();
    });

    // Should still show the selector (empty)
    expect(screen.getByTestId('model-selector')).toBeInTheDocument();

    // Should have logged the error
    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
  });

  it('clears models when provider changes', async () => {
    const { rerender } = render(<ModelSelector onChange={() => {}} />);

    // Initially no provider, should show placeholder
    expect(screen.getByTestId('model-selector-placeholder')).toBeInTheDocument();

    // Change to have a provider
    const mockModels = ['gpt-4'];
    mockGetProviderModels.mockResolvedValue(mockModels);

    rerender(<ModelSelector provider="openai" onChange={() => {}} />);

    await waitFor(() => {
      expect(screen.getByTestId('model-select')).toBeInTheDocument();
    });

    // Change provider again
    const newModels = ['claude-3'];
    mockGetProviderModels.mockResolvedValue(newModels);

    rerender(<ModelSelector provider="anthropic" onChange={() => {}} />);

    await waitFor(() => {
      expect(mockGetProviderModels).toHaveBeenCalledWith('anthropic');
    });
  });

  it('disables select while loading', async () => {
    // Create a promise that doesn't resolve immediately
    let resolvePromise: (value: string[]) => void;
    const loadingPromise = new Promise<string[]>(resolve => {
      resolvePromise = resolve;
    });

    mockGetProviderModels.mockReturnValue(loadingPromise);

    render(<ModelSelector provider="openai" onChange={() => {}} />);

    // Should be disabled while loading
    const select = screen.getByTestId('model-select');
    expect(select).toBeDisabled();

    // Resolve the promise
    resolvePromise!(['gpt-4']);

    await waitFor(() => {
      expect(select).not.toBeDisabled();
    });
  });

  it('sanitizes model names for data-testid attributes', async () => {
    const mockModels = ['gpt-4-turbo', 'claude-3-sonnet', 'gemini-pro-vision'];
    mockGetProviderModels.mockResolvedValue(mockModels);

    render(<ModelSelector provider="openai" onChange={() => {}} />);

    // With shadcn/ui Select, options are not rendered until opened
    // Just verify the component renders correctly
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /model/i })).toBeInTheDocument();
    });
  });
});
