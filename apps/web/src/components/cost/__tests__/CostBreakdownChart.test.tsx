import React from 'react';
import { render, screen } from '@testing-library/react';
import CostBreakdownChart from '../CostBreakdownChart';

vi.mock('recharts', () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: ({ name, fill }: { name?: string; fill?: string }) => (
    <div data-testid="bar" data-name={name} data-fill={fill} />
  ),
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: ({ tickFormatter }: { tickFormatter?: (value: number | string) => React.ReactNode }) => (
    <div data-testid="y-axis" data-tick={String(tickFormatter?.(3.21))} />
  ),
  CartesianGrid: () => <div data-testid="grid" />,
  Tooltip: ({ content }: { content?: React.ReactElement }) => (
    <div data-testid="tooltip">
      {React.isValidElement(content)
        ? React.cloneElement(content, {
            active: true,
            label: 'OpenAI',
            payload: [{ value: 3.21 }],
          })
        : null}
    </div>
  ),
  Legend: () => <div data-testid="legend" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

vi.mock('@/utils/format-cost', () => ({
  formatCost: (value: number) => `$${value.toFixed(2)}`,
}));

const originalGetComputedStyle = window.getComputedStyle;

beforeAll(() => {
  window.getComputedStyle = vi.fn().mockReturnValue({
    getPropertyValue: () => '#ffffff',
  }) as typeof window.getComputedStyle;
});

afterAll(() => {
  window.getComputedStyle = originalGetComputedStyle;
});

describe('CostBreakdownChart', () => {
  const sampleData = [
    { name: 'OpenAI', value: 15.5, color: '#4285f4' },
    { name: 'Anthropic', value: 8.3, color: '#34a853' },
    { name: 'Google', value: 3.2, color: '#fbbc04' },
  ];

  it('renders the chart shell and invokes the tooltip formatter', () => {
    render(<CostBreakdownChart data={sampleData} />);

    expect(screen.getByText('Cost Breakdown by Provider')).toBeInTheDocument();
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
    expect(screen.getByText('Cost: $3.21')).toBeInTheDocument();
    expect(screen.getByTestId('y-axis')).toHaveAttribute('data-tick', '$3.21');
    expect(screen.getAllByTestId('bar')).toHaveLength(3);
  });
});
