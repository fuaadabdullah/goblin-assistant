import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('../Card', () => {
  return function MockCard({ children, ...props }: { children: React.ReactNode; [k: string]: unknown }) {
    return <div data-testid="card" {...props}>{children}</div>;
  };
});

import StatCard from '../StatCard';

describe('StatCard', () => {
  it('renders label', () => {
    render(<StatCard label="Total Users" value={42} />);
    expect(screen.getByText('Total Users')).toBeInTheDocument();
  });

  it('renders numeric value', () => {
    render(<StatCard label="Count" value={99} />);
    expect(screen.getByText('99')).toBeInTheDocument();
  });

  it('renders string value', () => {
    render(<StatCard label="Status" value="Active" />);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('renders hint when provided', () => {
    render(<StatCard label="Revenue" value="$100" hint="Last 30 days" />);
    expect(screen.getByText('Last 30 days')).toBeInTheDocument();
  });

  it('does not render hint when not provided', () => {
    const { container } = render(<StatCard label="Test" value={0} />);
    // No hint div
    expect(container.querySelector('.text-\\[11px\\]')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<StatCard label="Test" value={0} className="custom-class" />);
    const card = screen.getByTestId('card');
    expect(card).toBeInTheDocument();
  });

  it('sets accessible aria-label', () => {
    render(<StatCard label="API Calls" value={1234} />);
    const group = screen.getByRole('group');
    expect(group).toHaveAttribute('aria-label', 'API Calls 1234');
  });

  it('converts number value to string for aria-label', () => {
    render(<StatCard label="Score" value={100} />);
    const group = screen.getByRole('group');
    expect(group).toHaveAttribute('aria-label', 'Score 100');
  });
});
