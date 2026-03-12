import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('@/utils/format-cost', () => ({
  formatCost: (v: number) => `$${v.toFixed(2)}`,
}));

import { CostOverviewBanner } from '../CostOverviewBanner';

describe('CostOverviewBanner', () => {
  const baseProps = {
    totalCost: 100.5,
    todayCost: 5.25,
    thisMonthCost: 42.0,
    byProvider: {},
  };

  it('renders the heading', () => {
    render(<CostOverviewBanner {...baseProps} />);
    expect(screen.getByText('Usage Overview')).toBeInTheDocument();
  });

  it('renders description text', () => {
    render(<CostOverviewBanner {...baseProps} />);
    expect(screen.getByText(/administrators/)).toBeInTheDocument();
  });

  it('displays total cost', () => {
    render(<CostOverviewBanner {...baseProps} />);
    expect(screen.getByText('$100.50')).toBeInTheDocument();
  });

  it('displays today cost', () => {
    render(<CostOverviewBanner {...baseProps} />);
    expect(screen.getByText('$5.25')).toBeInTheDocument();
  });

  it('displays this month cost', () => {
    render(<CostOverviewBanner {...baseProps} />);
    expect(screen.getByText('$42.00')).toBeInTheDocument();
  });

  it('shows provider breakdown when byProvider has entries', () => {
    render(
      <CostOverviewBanner
        {...baseProps}
        byProvider={{ openai: 50, anthropic: 30 }}
      />
    );
    expect(screen.getByText(/openai/)).toBeInTheDocument();
    expect(screen.getByText(/anthropic/)).toBeInTheDocument();
  });

  it('does not render provider section when byProvider is empty', () => {
    const { container } = render(<CostOverviewBanner {...baseProps} />);
    // The grid should exist but not the extra provider spans
    expect(container.querySelectorAll('.mt-4')).toHaveLength(0);
  });

  it('renders cost labels', () => {
    render(<CostOverviewBanner {...baseProps} />);
    expect(screen.getByText('Total cost')).toBeInTheDocument();
    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('This month')).toBeInTheDocument();
  });
});
