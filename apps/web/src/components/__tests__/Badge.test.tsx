import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Badge } from '../ui/Badge';

describe('Badge', () => {
  it('renders children', () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('has role="status"', () => {
    render(<Badge>Info</Badge>);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders an icon when provided', () => {
    render(<Badge icon={<span data-testid="badge-icon">✓</span>}>Done</Badge>);
    expect(screen.getByTestId('badge-icon')).toBeInTheDocument();
  });

  it('does not render icon when not provided', () => {
    const { container } = render(<Badge>No Icon</Badge>);
    expect(container.querySelector('[aria-hidden="true"]')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<Badge className="custom-badge">Styled</Badge>);
    expect(container.firstChild).toHaveClass('custom-badge');
  });
});
