'use client';

import type {
  VisualizationBlock,
  BarChartConfig,
  PieChartConfig,
  TableConfig,
  HeatmapConfig,
} from './types';
import FinanceBarChart from './FinanceBarChart';
import AllocationPie from './AllocationPie';
import ProjectionsTable from './ProjectionsTable';
import CorrelationHeatmap from './CorrelationHeatmap';

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
