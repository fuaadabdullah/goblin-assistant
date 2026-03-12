export type VisualizationType =
  | 'line_chart'
  | 'bar_chart'
  | 'pie_chart'
  | 'table'
  | 'heatmap';

export interface ColumnDef {
  key: string;
  label: string;
}

export interface BarDef {
  dataKey: string;
  label: string;
}

export interface BarChartConfig {
  xKey: string;
  bars: BarDef[];
}

export interface PieChartConfig {
  valueLabel?: string;
}

export interface TableConfig {
  columns: ColumnDef[];
  highlight?: { key: string; value: number | string | undefined };
}

export interface HeatmapConfig {
  rowKey: string;
  columns: string[];
  minValue: number;
  maxValue: number;
}

export type VisualizationConfig =
  | BarChartConfig
  | PieChartConfig
  | TableConfig
  | HeatmapConfig;

export interface VisualizationBlock {
  type: VisualizationType;
  title: string;
  data: Record<string, unknown>[];
  config: VisualizationConfig;
}
