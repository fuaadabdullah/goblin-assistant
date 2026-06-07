import React from 'react';
import { render, screen } from '@testing-library/react';
import FinanceBarChart from '../FinanceBarChart';

vi.mock('recharts', () => ({
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ResponsiveContainer: ({ children }: any) => <div data-testid="container">{children}</div>,
}));

describe('FinanceBarChart', () => {
  const mockData = [
    { month: 'Jan', value: 100 },
    { month: 'Feb', value: 150 },
    { month: 'Mar', value: 200 },
  ];

  const mockConfig = {
    xKey: 'month',
    bars: [{ dataKey: 'value', label: 'Value' }],
  };

  it('renders bar chart', () => {
    render(<FinanceBarChart title="Monthly Costs" data={mockData} config={mockConfig} />);
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('renders title', () => {
    render(<FinanceBarChart title="Monthly Costs" data={mockData} config={mockConfig} />);
    expect(screen.getByText('Monthly Costs')).toBeInTheDocument();
  });

  it('renders axes', () => {
    render(<FinanceBarChart title="Test" data={mockData} config={mockConfig} />);
    expect(screen.getByTestId('x-axis')).toBeInTheDocument();
    expect(screen.getByTestId('y-axis')).toBeInTheDocument();
  });

  it('renders tooltip', () => {
    render(<FinanceBarChart title="Test" data={mockData} config={mockConfig} />);
    expect(screen.getByTestId('tooltip')).toBeInTheDocument();
  });

  it('renders with empty data', () => {
    render(<FinanceBarChart title="Test" data={[]} config={mockConfig} />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
});
