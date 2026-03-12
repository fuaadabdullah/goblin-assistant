import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ProviderDetails from '../ProviderDetails';

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
  const onSetPriority = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders provider name and subtitle', () => {
    render(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    expect(screen.getByText('OpenAI')).toBeInTheDocument();
    expect(screen.getByText('Provider Configuration & Testing')).toBeInTheDocument();
  });

  it('shows enabled status', () => {
    render(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    expect(screen.getByText('Enabled')).toBeInTheDocument();
  });

  it('shows disabled status', () => {
    render(<ProviderDetails provider={{ ...baseProvider, enabled: false }} onSetPriority={onSetPriority} />);
    expect(screen.getByText('Disabled')).toBeInTheDocument();
  });

  it('shows priority value', () => {
    const { container } = render(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    const metrics = container.querySelectorAll('.bg-bg.rounded-lg.p-4');
    // Priority is 2nd metric
    expect(metrics[1]?.textContent).toContain('1');
  });

  it('shows N/A for missing priority', () => {
    const { container } = render(<ProviderDetails provider={{ ...baseProvider, priority: undefined }} onSetPriority={onSetPriority} />);
    const metrics = container.querySelectorAll('.bg-bg.rounded-lg.p-4');
    expect(metrics[1]?.textContent).toContain('N/A');
  });

  it('shows weight', () => {
    const { container } = render(<ProviderDetails provider={{ ...baseProvider, weight: 2.5 }} onSetPriority={onSetPriority} />);
    const metrics = container.querySelectorAll('.bg-bg.rounded-lg.p-4');
    expect(metrics[2]?.textContent).toContain('2.5');
  });

  it('shows model count', () => {
    const { container } = render(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    const metrics = container.querySelectorAll('.bg-bg.rounded-lg.p-4');
    expect(metrics[3]?.textContent).toContain('2');
  });

  it('shows 0 when no models', () => {
    const { container } = render(<ProviderDetails provider={{ ...baseProvider, models: undefined }} onSetPriority={onSetPriority} />);
    const metrics = container.querySelectorAll('.bg-bg.rounded-lg.p-4');
    expect(metrics[3]?.textContent).toContain('0');
  });

  it('calls onSetPriority as primary', () => {
    render(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    fireEvent.click(screen.getByText(/Set as Primary/));
    expect(onSetPriority).toHaveBeenCalledWith(1, 1, 'primary');
  });

  it('calls onSetPriority as fallback', () => {
    render(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    fireEvent.click(screen.getByText(/Set as Fallback/));
    expect(onSetPriority).toHaveBeenCalledWith(1, 10, 'fallback');
  });

  it('disables priority buttons when no id', () => {
    render(<ProviderDetails provider={{ ...baseProvider, id: undefined }} onSetPriority={onSetPriority} />);
    expect(screen.getByText(/Set as Primary/).closest('button')).toBeDisabled();
    expect(screen.getByText(/Set as Fallback/).closest('button')).toBeDisabled();
  });

  it('shows base URL', () => {
    render(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    const input = screen.getByLabelText('Base URL') as HTMLInputElement;
    expect(input.value).toBe('https://api.openai.com');
  });

  it('shows Not configured for missing base_url', () => {
    render(<ProviderDetails provider={{ ...baseProvider, base_url: undefined }} onSetPriority={onSetPriority} />);
    const input = screen.getByLabelText('Base URL') as HTMLInputElement;
    expect(input.value).toBe('Not configured');
  });

  it('shows configured API key status', () => {
    render(<ProviderDetails provider={baseProvider} onSetPriority={onSetPriority} />);
    expect(screen.getByText('✓ Configured')).toBeInTheDocument();
  });

  it('shows not configured API key status', () => {
    render(<ProviderDetails provider={{ ...baseProvider, api_key: undefined }} onSetPriority={onSetPriority} />);
    expect(screen.getByText('✗ Not configured')).toBeInTheDocument();
  });
});
