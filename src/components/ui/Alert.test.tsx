import { describe, it, expect, jest } from '@jest/globals';
import { render, fireEvent } from '@testing-library/react';
import Alert from './Alert';

describe('Alert', () => {
  it('renders with info variant by default', () => {
    const { getByText, getByRole } = render(<Alert message="Information message" />);

    const alert = getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(getByText('Information message')).toBeInTheDocument();
  });

  it('renders with different variants', () => {
    const { getByRole, rerender } = render(<Alert variant="success" message="Success!" />);

    let alert = getByRole('alert');
    expect(alert).toHaveClass('bg-success/10');

    rerender(<Alert variant="warning" message="Warning!" />);
    alert = getByRole('alert');
    expect(alert).toHaveClass('bg-warning/10');

    rerender(<Alert variant="danger" message="Error!" />);
    alert = getByRole('alert');
    expect(alert).toHaveClass('bg-danger/10');
  });

  it('renders with optional title', () => {
    const { getByText } = render(<Alert title="Alert Title" message="Alert message" />);

    expect(getByText('Alert Title')).toBeInTheDocument();
    expect(getByText('Alert message')).toBeInTheDocument();
  });

  it('renders ReactNode message', () => {
    const { getByText } = render(
      <Alert
        message={
          <>
            <p>First paragraph</p>
            <p>Second paragraph</p>
          </>
        }
      />
    );

    expect(getByText('First paragraph')).toBeInTheDocument();
    expect(getByText('Second paragraph')).toBeInTheDocument();
  });

  it('shows dismiss button when dismissible is true', () => {
  const onDismiss = jest.fn();
    const { getByRole } = render(
      <Alert message="Dismissible alert" dismissible onDismiss={onDismiss} />
    );

    const dismissButton = getByRole('button', { name: /dismiss/i });
    expect(dismissButton).toBeInTheDocument();

    fireEvent.click(dismissButton);
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('does not show dismiss button when dismissible is false', () => {
    const { queryByRole } = render(<Alert message="Non-dismissible alert" dismissible={false} />);

    const dismissButton = queryByRole('button', { name: /dismiss/i });
    expect(dismissButton).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { getByRole } = render(<Alert message="Custom alert" className="custom-class" />);

    const alert = getByRole('alert');
    expect(alert).toHaveClass('custom-class');
  });

  it('has proper ARIA attributes', () => {
    const { getByRole } = render(<Alert variant="danger" message="Error occurred" />);

    const alert = getByRole('alert');
    expect(alert).toHaveAttribute('role', 'alert');
    expect(alert).toHaveAttribute('aria-live', 'assertive');
  });
});
