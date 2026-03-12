'use client';

import type { HeatmapConfig } from './types';

interface CorrelationHeatmapProps {
  title: string;
  data: Record<string, unknown>[];
  config: HeatmapConfig;
}

function interpolateColor(value: number, min: number, max: number): string {
  // Normalize to 0–1 range
  const t = Math.max(0, Math.min(1, (value - min) / (max - min || 1)));

  // Red (negative) → White (zero) → Green (positive)
  if (t < 0.5) {
    // Red to white
    const ratio = t * 2;
    const r = 220;
    const g = Math.round(60 + ratio * 195);
    const b = Math.round(60 + ratio * 195);
    return `rgb(${r}, ${g}, ${b})`;
  }
  // White to green
  const ratio = (t - 0.5) * 2;
  const r = Math.round(255 - ratio * 195);
  const g = Math.round(255 - ratio * 35);
  const b = Math.round(255 - ratio * 195);
  return `rgb(${r}, ${g}, ${b})`;
}

const CorrelationHeatmap = ({ title, data, config }: CorrelationHeatmapProps) => {
  const { rowKey, columns, minValue, maxValue } = config;

  return (
    <div className="my-3 rounded-xl border border-border bg-surface/70 p-4 shadow-card">
      <h3 className="text-sm font-semibold text-text mb-3">{title}</h3>
      <div className="overflow-x-auto">
        <table className="border-collapse text-xs">
          <thead>
            <tr>
              <th className="border border-border bg-surface-hover px-3 py-1.5 text-left font-semibold text-text" />
              {columns.map((col) => (
                <th
                  key={col}
                  className="border border-border bg-surface-hover px-3 py-1.5 text-center font-semibold text-text"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIdx) => (
              <tr key={rowIdx}>
                <td className="border border-border bg-surface-hover px-3 py-1.5 font-semibold text-text">
                  {String(row[rowKey] ?? '')}
                </td>
                {columns.map((col) => {
                  const val = Number(row[col] ?? 0);
                  const bg = interpolateColor(val, minValue, maxValue);
                  // Dark text on light backgrounds, light text on dark
                  const textColor =
                    val > -0.3 && val < 0.7 ? 'rgba(0,0,0,0.8)' : 'rgba(255,255,255,0.9)';

                  return (
                    <td
                      key={col}
                      className="border border-border px-3 py-1.5 text-center font-mono"
                      style={{ backgroundColor: bg, color: textColor }}
                    >
                      {val.toFixed(2)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-2 mt-3 text-xs text-muted">
        <span>{minValue}</span>
        <div
          className="h-3 w-32 rounded"
          style={{
            background: `linear-gradient(to right, rgb(220, 60, 60), rgb(255, 255, 255), rgb(60, 220, 60))`,
          }}
        />
        <span>{maxValue}</span>
      </div>
    </div>
  );
};

export default CorrelationHeatmap;
