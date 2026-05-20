import React from 'react';
import { render, screen } from '@testing-library/react';

// Mock recharts
jest.mock('recharts', () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: ({ name }: { name?: string }) => <div data-testid="bar" data-name={name} />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="responsive-container">{children}</div>,
}));

jest.mock('@/utils/format-cost', () => ({
  formatCost: (value: number) => `$${value.toFixed(2)}`,
}));

// Mock getComputedStyle
const origGetComputedStyle = window.getComputedStyle;
beforeAll(() => {
  window.getComputedStyle = jest.fn().mockReturnValue({
    getPropertyValue: () => '#ffffff',
  });
});
afterAll(() => {
  window.getComputedStyle = origGetComputedStyle;
});

import CostBreakdownChart from '../CostBreakdownChart';

const sampleData = [
  { name: 'OpenAI', value: 15.5, color: '#4285f4' },
  { name: 'Anthropic', value: 8.3, color: '#34a853' },
  { name: 'Google', value: 3.2, color: '#fbbc04' },
];

describe('CostBreakdownChart', () => {
  it('renders heading', () => {
    render(<CostBreakdownChart data={sampleData} />);
    expect(screen.getByText('Cost Breakdown by Provider')).toBeInTheDocument();
  });

  it('renders responsive container', () => {
    render(<CostBreakdownChart data={sampleData} />);
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('renders bar chart', () => {
    render(<CostBreakdownChart data={sampleData} />);
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('renders a bar for each data entry', () => {
    render(<CostBreakdownChart data={sampleData} />);
    const bars = screen.getAllByTestId('bar');
    expect(bars).toHaveLength(3);
  });

  it('renders grid, axes, tooltip, and legend', () => {
    render(<CostBreakdownChart data={sampleData} />);
    expect(screen.getByTestId('grid')).toBeInTheDocument();
    expect(screen.getByTestId('x-axis')).toBeInTheDocument();
    expect(screen.getByTestId('y-axis')).toBeInTheDocument();
    expect(screen.getByTestId('tooltip')).toBeInTheDocument();
    expect(screen.getByTestId('legend')).toBeInTheDocument();
  });

  it('passes data entry names to bars', () => {
    render(<CostBreakdownChart data={sampleData} />);
    const bars = screen.getAllByTestId('bar');
    expect(bars[0]).toHaveAttribute('data-name', 'OpenAI');
    expect(bars[1]).toHaveAttribute('data-name', 'Anthropic');
  });

  it('renders with empty data', () => {
    render(<CostBreakdownChart data={[]} />);
    expect(screen.getByText('Cost Breakdown by Provider')).toBeInTheDocument();
    expect(screen.queryAllByTestId('bar')).toHaveLength(0);
  });
});
