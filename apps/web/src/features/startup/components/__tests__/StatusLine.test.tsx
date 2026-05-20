import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import StatusLine from '../StatusLine';

describe('StatusLine', () => {
  it('renders the label', () => {
    render(<StatusLine label="Loading config" state="active" />);
    expect(screen.getByText('Loading config')).toBeInTheDocument();
  });

  it('applies success color for complete state', () => {
    const { container } = render(<StatusLine label="Done" state="complete" />);
    expect(container.querySelector('.bg-success')).toBeInTheDocument();
    expect(container.querySelector('.text-success')).toBeInTheDocument();
  });

  it('applies primary color and pulse for active state', () => {
    const { container } = render(<StatusLine label="Active" state="active" />);
    expect(container.querySelector('.bg-primary')).toBeInTheDocument();
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('applies border color for pending state', () => {
    const { container } = render(<StatusLine label="Pending" state="pending" />);
    expect(container.querySelector('.bg-border')).toBeInTheDocument();
    expect(container.querySelector('.text-muted')).toBeInTheDocument();
  });

  it('applies danger color for error state', () => {
    const { container } = render(<StatusLine label="Error" state="error" />);
    expect(container.querySelector('.bg-danger')).toBeInTheDocument();
    expect(container.querySelector('.text-danger')).toBeInTheDocument();
  });
});
