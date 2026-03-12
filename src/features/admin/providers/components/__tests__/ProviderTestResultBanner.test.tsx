import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

import ProviderTestResultBanner from '../ProviderTestResultBanner';

describe('ProviderTestResultBanner', () => {
  const onDismiss = jest.fn();

  const successResult = {
    success: true,
    message: 'Connected OK',
    latency: 120,
    model_used: 'gpt-4',
    response: 'Hello world',
  };

  const failResult = {
    success: false,
    message: 'Connection refused',
    latency: 5000,
  };

  beforeEach(() => jest.clearAllMocks());

  it('shows success heading when successful', () => {
    render(<ProviderTestResultBanner result={successResult} onDismiss={onDismiss} />);
    expect(screen.getByText('Test Successful')).toBeInTheDocument();
  });

  it('shows failure heading when failed', () => {
    render(<ProviderTestResultBanner result={failResult} onDismiss={onDismiss} />);
    expect(screen.getByText('Test Failed')).toBeInTheDocument();
  });

  it('renders result message', () => {
    render(<ProviderTestResultBanner result={successResult} onDismiss={onDismiss} />);
    expect(screen.getByText('Connected OK')).toBeInTheDocument();
  });

  it('shows latency', () => {
    render(<ProviderTestResultBanner result={successResult} onDismiss={onDismiss} />);
    expect(screen.getByText('Latency: 120ms')).toBeInTheDocument();
  });

  it('shows model used', () => {
    render(<ProviderTestResultBanner result={successResult} onDismiss={onDismiss} />);
    expect(screen.getByText('Model: gpt-4')).toBeInTheDocument();
  });

  it('hides model when not present', () => {
    render(<ProviderTestResultBanner result={failResult} onDismiss={onDismiss} />);
    expect(screen.queryByText(/Model:/)).not.toBeInTheDocument();
  });

  it('shows sample response when present', () => {
    render(<ProviderTestResultBanner result={successResult} onDismiss={onDismiss} />);
    expect(screen.getByText('Sample Response:')).toBeInTheDocument();
    expect(screen.getByText('Hello world')).toBeInTheDocument();
  });

  it('hides sample response when not present', () => {
    render(<ProviderTestResultBanner result={failResult} onDismiss={onDismiss} />);
    expect(screen.queryByText('Sample Response:')).not.toBeInTheDocument();
  });

  it('calls onDismiss when dismiss clicked', () => {
    render(<ProviderTestResultBanner result={successResult} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByLabelText('Dismiss'));
    expect(onDismiss).toHaveBeenCalled();
  });

  it('renders success icon for success', () => {
    render(<ProviderTestResultBanner result={successResult} onDismiss={onDismiss} />);
    expect(screen.getByText('✓')).toBeInTheDocument();
  });

  it('renders failure icon for failure', () => {
    render(<ProviderTestResultBanner result={failResult} onDismiss={onDismiss} />);
    expect(screen.getByText('✗')).toBeInTheDocument();
  });
});
