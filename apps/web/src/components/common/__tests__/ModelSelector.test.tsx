import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

import ModelSelector from '../ModelSelector';
import { runtimeClient } from '@/lib/api/runtimeClient';

vi.mock('@/lib/api/runtimeClient', () => ({
  runtimeClient: {
    getProviderModelOptions: vi.fn(),
    getProviderModels: vi.fn(),
  },
}));

vi.mock('@/components/ui/Select', () => {
  type MockSelectProps = {
    children?: React.ReactNode;
    disabled?: boolean;
    placeholder?: string;
    [key: string]: unknown;
  };

  return {
    Select: ({ children, disabled }: MockSelectProps) => (
      <div data-testid="mock-select-root" data-disabled={disabled ? 'true' : 'false'}>
        {children}
      </div>
    ),
    SelectTrigger: ({ children, ...props }: MockSelectProps) => <div {...props}>{children}</div>,
    SelectValue: ({ placeholder }: MockSelectProps) => <span>{placeholder}</span>,
    SelectContent: ({ children }: MockSelectProps) => <div>{children}</div>,
    SelectItem: ({ children, disabled, ...props }: MockSelectProps) => (
      <div {...props} data-disabled={disabled ? 'true' : 'false'}>
        {children}
      </div>
    ),
  };
});

describe('ModelSelector', () => {
  const mockedRuntimeClient = runtimeClient as unknown as {
    getProviderModelOptions: vi.Mock;
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows placeholder when provider is not selected', () => {
    render(<ModelSelector onChange={vi.fn()} />);

    expect(screen.getByTestId('model-selector-placeholder')).toHaveTextContent(
      'Select a provider first'
    );
  });

  it('renders unhealthy models as disabled with reason text', async () => {
    mockedRuntimeClient.getProviderModelOptions.mockResolvedValue([
      {
        name: 'gpt-4o-mini',
        provider: 'openai',
        isSelectable: true,
        health: 'healthy',
        healthReason: null,
      },
      {
        name: 'gpt-4o',
        provider: 'openai',
        isSelectable: false,
        health: 'unhealthy',
        healthReason: 'Provider health check failed.',
      },
    ]);

    render(<ModelSelector provider="openai" selected="" onChange={vi.fn()} />);

    await waitFor(() => {
      expect(mockedRuntimeClient.getProviderModelOptions).toHaveBeenCalledWith('openai');
    });

    expect(screen.getByTestId('model-option-gpt-4o-mini')).toHaveAttribute(
      'data-disabled',
      'false'
    );
    expect(screen.getByTestId('model-option-gpt-4o')).toHaveAttribute('data-disabled', 'true');
    expect(screen.getByTestId('model-option-gpt-4o')).toHaveTextContent(
      'Unavailable: Provider health check failed.'
    );
  });
});
