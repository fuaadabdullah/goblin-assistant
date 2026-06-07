import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('../../ui/Alert', () => ({
  default: function MockAlert(props: { variant: string; title: string; message: string }) {
    return (
      <div data-testid="alert" data-variant={props.variant}>
        {props.message}
      </div>
    );
  },
}));

vi.mock('../../ui/Button', () => ({
  default: function MockButton({
    children,
    onClick,
  }: {
    children: React.ReactNode;
    onClick?: () => void;
  }) {
    return <button onClick={onClick}>{children}</button>;
  },
}));

import { DashboardError } from '../DashboardError';

describe('DashboardError', () => {
  const onRetry = vi.fn();

  beforeEach(() => vi.clearAllMocks());

  it('renders the error message', () => {
    render(<DashboardError error="Something went wrong" onRetry={onRetry} />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('renders the alert with danger variant', () => {
    render(<DashboardError error="fail" onRetry={onRetry} />);
    expect(screen.getByTestId('alert')).toHaveAttribute('data-variant', 'danger');
  });

  it('renders a retry button', () => {
    render(<DashboardError error="fail" onRetry={onRetry} />);
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('calls onRetry when retry is clicked', () => {
    render(<DashboardError error="fail" onRetry={onRetry} />);
    fireEvent.click(screen.getByText('Retry'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
