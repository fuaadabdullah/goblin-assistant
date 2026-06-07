import React from 'react';
import { render, screen } from '@testing-library/react';
import FinancialVisualization from '../FinancialVisualization';

vi.mock(
  '../AllocationPie',
  () => ({
    default: function MockPie(props: { title: string }) {
      return <div data-testid="allocation-pie">{props.title}</div>;
    },
  })
);

vi.mock(
  '../FinanceBarChart',
  () => ({
    default: function MockBarChart(props: { title: string }) {
      return <div data-testid="finance-bar-chart">{props.title}</div>;
    },
  })
);

vi.mock(
  '../ProjectionsTable',
  () => ({
    default: function MockTable(props: { title: string }) {
      return <div data-testid="projections-table">{props.title}</div>;
    },
  })
);

vi.mock(
  '../CorrelationHeatmap',
  () => ({
    default: function MockHeatmap(props: { title: string }) {
      return <div data-testid="correlation-heatmap">{props.title}</div>;
    },
  })
);

describe('FinancialVisualization', () => {
  it('renders bar_chart block', () => {
    render(
      <FinancialVisualization
        block={{
          type: 'bar_chart',
          title: 'Monthly Costs',
          data: [{ month: 'Jan', cost: 100 }],
          config: { xKey: 'month', bars: [{ dataKey: 'cost', label: 'Cost' }] },
        }}
      />
    );
    expect(screen.getByTestId('finance-bar-chart')).toBeInTheDocument();
    expect(screen.getByText('Monthly Costs')).toBeInTheDocument();
  });

  it('renders pie_chart block', () => {
    render(
      <FinancialVisualization
        block={{
          type: 'pie_chart',
          title: 'Allocation',
          data: [{ name: 'OpenAI', value: 50 }],
          config: {},
        }}
      />
    );
    expect(screen.getByTestId('allocation-pie')).toBeInTheDocument();
    expect(screen.getByText('Allocation')).toBeInTheDocument();
  });

  it('renders table block', () => {
    render(
      <FinancialVisualization
        block={{
          type: 'table',
          title: 'Projections',
          data: [{ provider: 'OpenAI', q1: 100 }],
          config: { columns: [{ key: 'provider', label: 'Provider' }] },
        }}
      />
    );
    expect(screen.getByTestId('projections-table')).toBeInTheDocument();
    expect(screen.getByText('Projections')).toBeInTheDocument();
  });

  it('renders heatmap block', () => {
    render(
      <FinancialVisualization
        block={{
          type: 'heatmap',
          title: 'Correlation',
          data: [{ provider: 'OpenAI', openai: 1.0 }],
          config: { rowKey: 'provider', columns: ['openai'], minValue: 0, maxValue: 1 },
        }}
      />
    );
    expect(screen.getByTestId('correlation-heatmap')).toBeInTheDocument();
    expect(screen.getByText('Correlation')).toBeInTheDocument();
  });

  it('renders line_chart block as bar chart', () => {
    render(
      <FinancialVisualization
        block={{
          type: 'line_chart',
          title: 'Trend',
          data: [{ month: 'Jan', cost: 100 }],
          config: { xKey: 'month', bars: [{ dataKey: 'cost', label: 'Cost' }] },
        }}
      />
    );
    expect(screen.getByTestId('finance-bar-chart')).toBeInTheDocument();
  });

  it('renders nothing for unknown type', () => {
    const { container } = render(
      <FinancialVisualization
        block={
          {
            type: 'unknown' as never,
            title: 'Unknown',
            data: [],
            config: {},
          } as never
        }
      />
    );
    expect(container.firstChild).toBeNull();
  });
});
