import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

jest.mock('lucide-react', () =>
  new Proxy({}, {
    get: (_, name) => {
      if (name === '__esModule') return true;
      return (props: Record<string, unknown>) => <span data-testid={`icon-${String(name)}`} {...props} />;
    },
  })
);

import ChatErrorBubble from '../ChatErrorBubble';
import type { UiError } from '../../../../lib/ui-error';

describe('ChatErrorBubble', () => {
  const baseError: UiError = {
    userMessage: 'Something went wrong',
    code: 'TEST_ERR',
    name: 'UiError',
    message: 'Something went wrong',
  };

  const defaultProps = { error: baseError, onDismiss: jest.fn() };

  beforeEach(() => jest.clearAllMocks());

  it('renders user message', () => {
    render(<ChatErrorBubble {...defaultProps} />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('renders error code', () => {
    render(<ChatErrorBubble {...defaultProps} />);
    expect(screen.getByText(/TEST_ERR/)).toBeInTheDocument();
  });

  it('hides error code when not present', () => {
    const error = { ...baseError, code: undefined };
    render(<ChatErrorBubble {...defaultProps} error={error} />);
    expect(screen.queryByText(/Error:/)).not.toBeInTheDocument();
  });

  it('shows dismiss button', () => {
    render(<ChatErrorBubble {...defaultProps} />);
    expect(screen.getByLabelText('Dismiss error')).toBeInTheDocument();
  });

  it('calls onDismiss when dismiss clicked', () => {
    render(<ChatErrorBubble {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('Dismiss error'));
    expect(defaultProps.onDismiss).toHaveBeenCalled();
  });

  it('shows retry button when onRetry provided', () => {
    render(<ChatErrorBubble {...defaultProps} onRetry={jest.fn()} />);
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('calls onRetry when retry clicked', () => {
    const onRetry = jest.fn();
    render(<ChatErrorBubble {...defaultProps} onRetry={onRetry} />);
    fireEvent.click(screen.getByText('Retry'));
    expect(onRetry).toHaveBeenCalled();
  });

  it('hides retry when onRetry not provided', () => {
    render(<ChatErrorBubble {...defaultProps} />);
    expect(screen.queryByText('Retry')).not.toBeInTheDocument();
  });
});
