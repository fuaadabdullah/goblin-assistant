import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import FinancialVisualization from '../FinancialVisualization';

jest.mock(
  '../AllocationPie',
  () =>
    function MockPie(props: any) {
      return <div data-testid="allocation-pie">{props.title}</div>;
    }
);

jest.mock(
  '../FinanceBarChart',
  () =>
    function MockBarChart(props: any) {
      return <div data-testid="finance-bar-chart">{props.title}</div>;
    }
);

jest.mock(
  '../ProjectionsTable',
  () =>
    function MockTable(props: any) {
      return <div data-testid="projections-table">{props.title}</div>;
    }
);

jest.mock(
  '../CorrelationHeatmap',
  () =>
    function MockHeatmap(props: any) {
      return <div data-testid="correlation-heatmap">{props.title}</div>;
    }
);

describe('FinancialVisualization', () => {
  const mockData = {
    allocation: [
      { name: 'OpenAI', value: 50 },
      { name: 'Anthropic', value: 30 },
    ],
    timeline: [
      { month: 'Jan', cost: 100 },
      { month: 'Feb', cost: 150 },
    ],
    projections: [{ provider: 'OpenAI', q1: 100, q2: 120 }],
    correlation: [{ provider: 'OpenAI', openai: 1.0 }],
  };

  it('renders financial visualization container', () => {
    const { container } = render(<FinancialVisualization data={mockData} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('renders allocation pie chart', () => {
    render(<FinancialVisualization data={mockData} />);
    expect(screen.getByTestId('allocation-pie')).toBeInTheDocument();
  });

  it('renders finance bar chart', () => {
    render(<FinancialVisualization data={mockData} />);
    expect(screen.getByTestId('finance-bar-chart')).toBeInTheDocument();
  });

  it('renders projections table', () => {
    render(<FinancialVisualization data={mockData} />);
    expect(screen.getByTestId('projections-table')).toBeInTheDocument();
  });

  it('renders correlation heatmap', () => {
    render(<FinancialVisualization data={mockData} />);
    expect(screen.getByTestId('correlation-heatmap')).toBeInTheDocument();
  });

  it('renders with partial data', () => {
    const partialData = {
      allocation: mockData.allocation,
    };
    const { container } = render(<FinancialVisualization data={partialData} />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
