import React from 'react';
import { render, screen } from '@testing-library/react';
import ProviderUsageChart from '../ProviderUsageChart';

vi.mock('recharts', () => ({
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: ({
    children,
    label,
  }: {
    children: React.ReactNode;
    label?: (props: { name?: string; percent?: number }) => React.ReactNode;
  }) => (
    <div data-testid="pie" data-label={String(label?.({ name: 'openai', percent: 0.5 }))}>
      {children}
    </div>
  ),
  Cell: ({ fill }: { fill?: string }) => <span data-testid="cell" data-fill={fill} />,
  Tooltip: ({ content }: { content?: React.ReactElement }) => (
    <div data-testid="tooltip">
      {React.isValidElement(content)
        ? React.cloneElement(content, {
            active: true,
            payload: [{ name: 'openai', value: 12.34 }],
          })
        : null}
    </div>
  ),
  Legend: ({ iconType }: { iconType?: string }) => (
    <div data-testid="legend" data-icon-type={iconType} />
  ),
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: ({ children, name }: { children: React.ReactNode; name?: string }) => (
    <div data-testid="bar" data-name={name}>
      {children}
    </div>
  ),
  CartesianGrid: () => <div data-testid="grid" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: ({
    tickFormatter,
  }: {
    tickFormatter?: (value: number | string) => React.ReactNode;
  }) => <div data-testid="y-axis" data-tick={String(tickFormatter?.(12.34))} />,
}));

vi.mock('@/utils/format-cost', () => ({
  formatCost: (value: number) => `$${value.toFixed(2)}`,
}));

describe('ProviderUsageChart', () => {
  it('renders a request chart with tooltip and label helpers', () => {
    render(
      <ProviderUsageChart
        metric="requests"
        data={[
          { name: 'openai', value: 12 },
          { name: 'anthropic', value: 8 },
        ]}
      />
    );

    expect(screen.getByRole('heading', { name: 'Provider Requests' })).toBeInTheDocument();
    expect(screen.getByTestId('pie')).toHaveAttribute('data-label', 'openai 50%');
    expect(screen.getByText('Requests: 12.34')).toBeInTheDocument();
    expect(screen.getAllByTestId('cell')).toHaveLength(2);
  });

  it('renders a cost chart with formatted ticks and tooltip text', () => {
    render(
      <ProviderUsageChart
        metric="cost"
        data={[
          { name: 'openai', value: 1.23 },
          { name: 'anthropic', value: 0.45 },
        ]}
      />
    );

    expect(screen.getByRole('heading', { name: 'Provider Costs' })).toBeInTheDocument();
    expect(screen.getByTestId('y-axis')).toHaveAttribute('data-tick', '$12.34');
    expect(screen.getByText('Cost: $12.34')).toBeInTheDocument();
    expect(screen.getAllByTestId('bar')).toHaveLength(1);
  });
});
