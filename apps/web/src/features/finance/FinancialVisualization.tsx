'use client';

import dynamic from 'next/dynamic';
import type {
  VisualizationBlock,
  BarChartConfig,
  PieChartConfig,
  TableConfig,
  HeatmapConfig,
} from './types';
import ProjectionsTable from './ProjectionsTable';
import CorrelationHeatmap from './CorrelationHeatmap';

const ChartSkeleton = () => (
  <div className="my-3 rounded-xl border border-border bg-surface/70 p-4 animate-pulse">
    <div className="h-4 w-32 bg-surface-hover rounded mb-3" />
    <div className="h-[260px] bg-surface-hover rounded-lg" />
  </div>
);

const FinanceBarChart = dynamic(() => import('./FinanceBarChart'), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});
const AllocationPie = dynamic(() => import('./AllocationPie'), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

interface FinancialVisualizationProps {
  block: VisualizationBlock;
}

const FinancialVisualization = ({ block }: FinancialVisualizationProps) => {
  switch (block.type) {
    case 'bar_chart':
      return (
        <FinanceBarChart
          title={block.title}
          data={block.data}
          config={block.config as BarChartConfig}
        />
      );
    case 'pie_chart':
      return (
        <AllocationPie
          title={block.title}
          data={block.data}
          config={block.config as PieChartConfig}
        />
      );
    case 'table':
      return (
        <ProjectionsTable
          title={block.title}
          data={block.data}
          config={block.config as TableConfig}
        />
      );
    case 'heatmap':
      return (
        <CorrelationHeatmap
          title={block.title}
          data={block.data}
          config={block.config as HeatmapConfig}
        />
      );
    case 'line_chart':
      // Reuse bar chart for now; line_chart type can be added later
      return (
        <FinanceBarChart
          title={block.title}
          data={block.data}
          config={block.config as BarChartConfig}
        />
      );
    default:
      return null;
  }
};

export default FinancialVisualization;
