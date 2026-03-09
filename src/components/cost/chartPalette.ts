export const CHART_COLOR_PALETTE = [
  'var(--primary)',
  'var(--accent)',
  'var(--cta)',
  'var(--success)',
  'var(--warning)',
  'var(--info)',
] as const;

export const getChartPaletteColor = (index: number) =>
  CHART_COLOR_PALETTE[index % CHART_COLOR_PALETTE.length];
