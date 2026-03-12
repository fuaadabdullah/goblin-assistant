import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('@/utils/format-cost', () => ({
  formatCost: (v: number) => `$${v.toFixed(2)}`,
}));

import CostPanel from '../CostPanel';

describe('CostPanel', () => {
  it('returns null when costSummary is null', () => {
    const { container } = render(<CostPanel costSummary={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('returns null when costSummary is undefined', () => {
    const { container } = render(<CostPanel />);
    expect(container.firstChild).toBeNull();
  });

  it('renders cost summary heading', () => {
    render(
      <CostPanel
        costSummary={{
          total_cost: 50.0,
          cost_by_provider: { openai: 30, anthropic: 20 },
          cost_by_model: { 'gpt-4': 30, 'claude-3': 20 },
        }}
      />
    );
    expect(screen.getByText('Cost Summary')).toBeInTheDocument();
  });

  it('renders total cost', () => {
    render(
      <CostPanel
        costSummary={{
          total_cost: 99.99,
          cost_by_provider: {},
          cost_by_model: {},
        }}
      />
    );
    expect(screen.getByText('$99.99')).toBeInTheDocument();
  });

  it('renders providers', () => {
    render(
      <CostPanel
        costSummary={{
          total_cost: 50.0,
          cost_by_provider: { openai: 30, anthropic: 20 },
          cost_by_model: {},
        }}
      />
    );
    expect(screen.getByText('By Provider:')).toBeInTheDocument();
    expect(screen.getByText(/openai/)).toBeInTheDocument();
    expect(screen.getByText(/anthropic/)).toBeInTheDocument();
  });

  it('renders models', () => {
    render(
      <CostPanel
        costSummary={{
          total_cost: 50.0,
          cost_by_provider: {},
          cost_by_model: { 'gpt-4': 30, 'claude-3': 20 },
        }}
      />
    );
    expect(screen.getByText('By Model:')).toBeInTheDocument();
    expect(screen.getByText(/gpt-4/)).toBeInTheDocument();
    expect(screen.getByText(/claude-3/)).toBeInTheDocument();
  });
});
