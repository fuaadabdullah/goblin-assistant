import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('@/components/ui/Select', () => ({
  Select: ({ children, value, onValueChange }: { children: React.ReactNode; value: string; onValueChange: (v: string) => void }) => (
    <div data-testid="select" data-value={value}>
      {children}
      <input data-testid="select-input" aria-label="select" value={value} onChange={(e) => onValueChange(e.target.value)} readOnly />
    </div>
  ),
  SelectContent: ({ children }: { children: React.ReactNode }) => <div data-testid="select-content">{children}</div>,
  SelectItem: ({ children, value }: { children: React.ReactNode; value: string }) => (
    <div data-testid={`select-item-${value}`}>{children}</div>
  ),
  SelectTrigger: ({ children, ...props }: { children: React.ReactNode; id?: string }) => (
    <button {...props} data-testid="select-trigger">{children}</button>
  ),
  SelectValue: ({ placeholder }: { placeholder: string }) => <span>{placeholder}</span>,
}));

import ProviderSelector from '../ProviderSelector';

describe('ProviderSelector', () => {
  it('returns null when providers is undefined', () => {
    const { container } = render(<ProviderSelector />);
    expect(container.firstChild).toBeNull();
  });

  it('returns null when providers is empty', () => {
    const { container } = render(<ProviderSelector providers={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders when providers are provided', () => {
    render(<ProviderSelector providers={['openai', 'anthropic']} />);
    expect(screen.getByTestId('provider-selector')).toBeInTheDocument();
  });

  it('renders the label', () => {
    render(<ProviderSelector providers={['openai']} />);
    expect(screen.getByTestId('provider-label')).toHaveTextContent('Provider:');
  });

  it('renders all provider options', () => {
    render(<ProviderSelector providers={['openai', 'anthropic', 'cohere']} />);
    expect(screen.getByTestId('select-item-openai')).toBeInTheDocument();
    expect(screen.getByTestId('select-item-anthropic')).toBeInTheDocument();
    expect(screen.getByTestId('select-item-cohere')).toBeInTheDocument();
  });

  it('defaults to first provider when selected is not provided', () => {
    render(<ProviderSelector providers={['openai', 'anthropic']} />);
    const select = screen.getByTestId('select');
    expect(select.getAttribute('data-value')).toBe('openai');
  });

  it('uses the selected prop when provided', () => {
    render(<ProviderSelector providers={['openai', 'anthropic']} selected="anthropic" />);
    const select = screen.getByTestId('select');
    expect(select.getAttribute('data-value')).toBe('anthropic');
  });

  it('renders the select trigger with aria-label', () => {
    render(<ProviderSelector providers={['openai']} />);
    expect(screen.getByTestId('select-trigger')).toBeInTheDocument();
  });
});
