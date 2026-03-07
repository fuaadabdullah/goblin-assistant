import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

import ModelSelector from '../ModelSelector';
import { runtimeClient } from '@/api/api-client';

jest.mock('@/api/api-client', () => ({
  runtimeClient: {
    getProviderModelOptions: jest.fn(),
    getProviderModels: jest.fn(),
  },
}));

jest.mock('@/components/ui/Select', () => {
  const React = require('react');

  return {
    Select: ({ children, disabled }: any) => (
      <div data-testid="mock-select-root" data-disabled={disabled ? 'true' : 'false'}>
        {children}
      </div>
    ),
    SelectTrigger: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
    SelectContent: ({ children }: any) => <div>{children}</div>,
    SelectItem: ({ children, disabled, ...props }: any) => (
      <div {...props} data-disabled={disabled ? 'true' : 'false'}>
        {children}
      </div>
    ),
  };
});

describe('ModelSelector', () => {
  const mockedRuntimeClient = runtimeClient as unknown as {
    getProviderModelOptions: jest.Mock;
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows placeholder when provider is not selected', () => {
    render(<ModelSelector onChange={jest.fn()} />);

    expect(screen.getByTestId('model-selector-placeholder')).toHaveTextContent(
      'Select a provider first',
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

    render(
      <ModelSelector
        provider="openai"
        selected=""
        onChange={jest.fn()}
      />,
    );

    await waitFor(() => {
      expect(mockedRuntimeClient.getProviderModelOptions).toHaveBeenCalledWith('openai');
    });

    expect(screen.getByTestId('model-option-gpt-4o-mini')).toHaveAttribute(
      'data-disabled',
      'false',
    );
    expect(screen.getByTestId('model-option-gpt-4o')).toHaveAttribute(
      'data-disabled',
      'true',
    );
    expect(screen.getByTestId('model-option-gpt-4o')).toHaveTextContent(
      'Unavailable: Provider health check failed.',
    );
  });
});
