import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import Alert from '../ui/Alert';

// The Alert component imports IconButton from ui/IconButton which uses
// class-variance-authority and cn. We mock it to avoid dependency issues.
jest.mock('../ui/IconButton', () => {
  return function MockIconButton({ onClick, 'aria-label': ariaLabel }: any) {
    return (
      <button aria-label={ariaLabel} onClick={onClick}>
        ✕
      </button>
    );
  };
});

describe('Alert', () => {
  it('renders the message', () => {
    render(<Alert message="This is an alert" />);
    expect(screen.getByText('This is an alert')).toBeInTheDocument();
  });

  it('renders the title when provided', () => {
    render(<Alert title="Warning" message="Something happened" />);
    expect(screen.getByText('Warning')).toBeInTheDocument();
  });

  it('does not render title when not provided', () => {
    render(<Alert message="Just a message" />);
    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
  });

  it('has role="alert"', () => {
    render(<Alert message="Alert!" />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('uses assertive live region for danger variant', () => {
    render(<Alert message="Error!" variant="danger" />);
    expect(screen.getByRole('alert')).toHaveAttribute('aria-live', 'assertive');
  });

  it('uses polite live region for info variant', () => {
    render(<Alert message="Info" variant="info" />);
    expect(screen.getByRole('alert')).toHaveAttribute('aria-live', 'polite');
  });

  it('renders a custom icon when provided', () => {
    render(<Alert message="Test" icon={<span data-testid="custom-icon">🔥</span>} />);
    expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
  });

  it('shows dismiss button when dismissible and onDismiss provided', () => {
    const onDismiss = jest.fn();
    render(<Alert message="Dismiss me" dismissible onDismiss={onDismiss} />);
    expect(screen.getByLabelText('Dismiss alert')).toBeInTheDocument();
  });

  it('does not show dismiss button when dismissible is false', () => {
    render(<Alert message="No dismiss" />);
    expect(screen.queryByLabelText('Dismiss alert')).not.toBeInTheDocument();
  });

  it('calls onDismiss when dismiss button is clicked', () => {
    const onDismiss = jest.fn();
    render(<Alert message="Dismiss me" dismissible onDismiss={onDismiss} />);
    fireEvent.click(screen.getByLabelText('Dismiss alert'));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('applies custom className', () => {
    const { container } = render(<Alert message="Styled" className="my-custom-class" />);
    const alertElement = container.firstChild as HTMLElement;
    expect(alertElement.className).toContain('my-custom-class');
  });
});
