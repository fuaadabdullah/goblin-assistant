import { describe, it, expect } from '@jest/globals';
import { render } from '@testing-library/react';
import Badge from './Badge';

describe('Badge', () => {
  it('renders with success variant styling', () => {
    const { getByRole } = render(<Badge variant="success">Healthy</Badge>);
    const badge = getByRole('status');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('text-success');
  });

  it('renders with warning variant styling', () => {
    const { getByRole } = render(<Badge variant="warning">Warning</Badge>);
    const badge = getByRole('status');
    expect(badge).toHaveClass('text-warning');
  });

  it('renders with danger variant styling', () => {
    const { getByRole } = render(<Badge variant="danger">Error</Badge>);
    const badge = getByRole('status');
    expect(badge).toHaveClass('text-danger');
  });

  it('renders with neutral variant by default', () => {
    const { getByRole } = render(<Badge>Neutral</Badge>);
    const badge = getByRole('status');
    expect(badge).toHaveClass('text-muted');
  });

  it('renders with different sizes', () => {
    const { getByRole, rerender } = render(<Badge size="sm">Small</Badge>);
    let badge = getByRole('status');
    expect(badge).toHaveClass('text-xs');

    rerender(<Badge size="md">Medium</Badge>);
    badge = getByRole('status');
    expect(badge).toHaveClass('text-sm');
  });

  it('renders with icon', () => {
    const { getByText } = render(<Badge icon="✓">Success</Badge>);
    const badge = getByText('Success');
    expect(badge.parentElement).toHaveTextContent('✓');
  });

  it('applies className prop', () => {
    const { getByRole } = render(
      <Badge variant="success" className="custom-class">
        Custom
      </Badge>
    );
    const badge = getByRole('status');
    expect(badge).toHaveClass('custom-class');
    expect(badge).toHaveClass('text-success');
  });

  it('renders with accessible role and aria-live', () => {
    const { getByRole } = render(<Badge variant="success">Active</Badge>);
    const badge = getByRole('status');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute('aria-live', 'polite');
  });
});
