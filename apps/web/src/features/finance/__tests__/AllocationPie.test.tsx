import React from 'react';
import { render, screen } from '@testing-library/react';
import AllocationPie from '../AllocationPie';

vi.mock('recharts', () => ({
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: ({ children }: any) => <div data-testid="pie">{children}</div>,
  Cell: () => <div data-testid="cell" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ResponsiveContainer: ({ children }: any) => <div data-testid="container">{children}</div>,
}));

vi.mock('@/components/cost/chartPalette', () => ({
  getChartPaletteColor: (i: number) => '#fff',
}));

describe('AllocationPie', () => {
  const mockData = [
    { name: 'OpenAI', value: 50 },
    { name: 'Anthropic', value: 30 },
    { name: 'Gemini', value: 20 },
  ];

  const mockConfig = {
    valueLabel: '%',
  };

  it('renders pie chart container', () => {
    render(<AllocationPie title="Cost Allocation" data={mockData} config={mockConfig} />);
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
  });

  it('renders title', () => {
    render(<AllocationPie title="Cost Allocation" data={mockData} config={mockConfig} />);
    expect(screen.getByText('Cost Allocation')).toBeInTheDocument();
  });

  it('renders legend', () => {
    render(<AllocationPie title="Cost Allocation" data={mockData} config={mockConfig} />);
    expect(screen.getByTestId('legend')).toBeInTheDocument();
  });

  it('renders tooltip', () => {
    render(<AllocationPie title="Cost Allocation" data={mockData} config={mockConfig} />);
    expect(screen.getByTestId('tooltip')).toBeInTheDocument();
  });

  it('renders with empty data', () => {
    render(<AllocationPie title="Cost Allocation" data={[]} config={mockConfig} />);
    expect(screen.getByText('Cost Allocation')).toBeInTheDocument();
  });

  it('renders color cells for each data item', () => {
    const { container } = render(
      <AllocationPie title="Cost Allocation" data={mockData} config={mockConfig} />
    );
    const cells = container.querySelectorAll('[data-testid="cell"]');
    expect(cells.length).toBe(mockData.length);
  });
});
