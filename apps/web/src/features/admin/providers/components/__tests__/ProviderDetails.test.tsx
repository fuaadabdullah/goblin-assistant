import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProviderDetails from '../ProviderDetails';

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const baseProvider = {
  name: 'OpenAI',
  enabled: true,
  id: 1,
  priority: 1,
  weight: 1.0,
  api_key: 'sk-***',
  base_url: 'https://api.openai.com',
  models: ['gpt-4', 'gpt-3.5-turbo'],
};

describe('ProviderDetails', () => {
  const onSetPriority = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders provider name and subtitle', () => {
    renderWithQuery(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    expect(screen.getByText('OpenAI')).toBeInTheDocument();
    expect(screen.getByText('Provider Configuration & Testing')).toBeInTheDocument();
  });

  it('shows enabled status', () => {
    renderWithQuery(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    expect(screen.getByText('Enabled')).toBeInTheDocument();
  });

  it('shows disabled status', () => {
    renderWithQuery(
      <ProviderDetails
        provider={{ ...baseProvider, enabled: false }}
        onSetPriority={onSetPriority}
      />
    );
    expect(screen.getByText('Disabled')).toBeInTheDocument();
  });

  it('shows priority value', () => {
    const { container } = renderWithQuery(
      <ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />
    );
    const metrics = container.querySelectorAll('.bg-bg.rounded-lg.p-4');
    // Priority is 2nd metric
    expect(metrics[1]?.textContent).toContain('1');
  });

  it('shows N/A for missing priority', () => {
    const { container } = renderWithQuery(
      <ProviderDetails
        provider={{ ...baseProvider, priority: undefined }}
        onSetPriority={onSetPriority}
      />
    );
    const metrics = container.querySelectorAll('.bg-bg.rounded-lg.p-4');
    expect(metrics[1]?.textContent).toContain('N/A');
  });

  it('shows weight', () => {
    const { container } = renderWithQuery(
      <ProviderDetails provider={{ ...baseProvider, weight: 2.5 }} onSetPriority={onSetPriority} />
    );
    const metrics = container.querySelectorAll('.bg-bg.rounded-lg.p-4');
    expect(metrics[2]?.textContent).toContain('2.5');
  });

  it('shows model count', () => {
    const { container } = renderWithQuery(
      <ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />
    );
    const metrics = container.querySelectorAll('.bg-bg.rounded-lg.p-4');
    expect(metrics[3]?.textContent).toContain('2');
  });

  it('shows 0 when no models', () => {
    const { container } = renderWithQuery(
      <ProviderDetails
        provider={{ ...baseProvider, models: undefined }}
        onSetPriority={onSetPriority}
      />
    );
    const metrics = container.querySelectorAll('.bg-bg.rounded-lg.p-4');
    expect(metrics[3]?.textContent).toContain('0');
  });

  it('calls onSetPriority as primary', () => {
    renderWithQuery(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    fireEvent.click(screen.getByText(/Set as Primary/));
    expect(onSetPriority).toHaveBeenCalledWith(1, 1, 'primary');
  });

  it('calls onSetPriority as fallback', () => {
    renderWithQuery(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    fireEvent.click(screen.getByText(/Set as Fallback/));
    expect(onSetPriority).toHaveBeenCalledWith(1, 10, 'fallback');
  });

  it('disables priority buttons when no id', () => {
    renderWithQuery(
      <ProviderDetails
        provider={{ ...baseProvider, id: undefined }}
        onSetPriority={onSetPriority}
      />
    );
    expect(screen.getByText(/Set as Primary/).closest('button')).toBeDisabled();
    expect(screen.getByText(/Set as Fallback/).closest('button')).toBeDisabled();
  });

  it('shows base URL', () => {
    renderWithQuery(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    const input = screen.getByLabelText('Base URL') as HTMLInputElement;
    expect(input.value).toBe('https://api.openai.com');
  });

  it('shows Not configured for missing base_url', () => {
    renderWithQuery(
      <ProviderDetails
        provider={{ ...baseProvider, base_url: undefined }}
        onSetPriority={onSetPriority}
      />
    );
    const input = screen.getByLabelText('Base URL') as HTMLInputElement;
    expect(input.value).toBe('Not configured');
  });

  it('shows configured API key status', () => {
    renderWithQuery(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    expect(screen.getByText('✓ Configured')).toBeInTheDocument();
  });

  it('shows not configured API key status', () => {
    renderWithQuery(
      <ProviderDetails
        provider={{ ...baseProvider, api_key: undefined }}
        onSetPriority={onSetPriority}
      />
    );
    expect(screen.getByText('✗ Not configured')).toBeInTheDocument();
  });
});
