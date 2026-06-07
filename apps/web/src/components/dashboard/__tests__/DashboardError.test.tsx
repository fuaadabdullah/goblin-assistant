import { render, screen, fireEvent } from '@testing-library/react';
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
    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveClass('border-danger');
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
