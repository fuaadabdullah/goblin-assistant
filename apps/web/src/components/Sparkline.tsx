import { useMemo } from 'react';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  strokeWidth?: number;
  color?: string;
  fillColor?: string;
  showFill?: boolean;
  className?: string;
}

/**
 * Sparkline - Minimal line chart for showing trends
 * Perfect for dashboard metrics like API latency over time
 */
export default function Sparkline({
  data,
  width = 100,
  height = 30,
  strokeWidth = 2,
  color, // Will use CSS variable if not provided
  fillColor,
  showFill = false,
  className = '',
}: SparklineProps) {
  // Use CSS variable for default color
  const defaultColor = 'var(--primary)';
  const strokeColor = color || defaultColor;
  const fillColorValue = fillColor || strokeColor;
  const { pathData, fillPath } = useMemo(() => {
    if (!data || data.length === 0) {
      return { pathData: '', fillPath: '' };
    }

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1; // Avoid division by zero

    // Calculate points
    const points = data.map((value, index) => {
      const normalizedX = (index / (data.length - 1 || 1)) * width;
      const normalizedY = height - ((value - min) / range) * height;
      return { x: normalizedX, y: normalizedY };
    });

    // Create line path
    const pathData = points
      .map((point, index) => {
        return `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)},${point.y.toFixed(2)}`;
      })
      .join(' ');

    // Create fill path (area under line)
    const fillPath = showFill ? `${pathData} L ${width},${height} L 0,${height} Z` : '';

    return { pathData, fillPath };
  }, [data, width, height, showFill]);

  if (!data || data.length === 0) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ width, height }}>
        <span className="text-xs text-muted">No data</span>
      </div>
    );
  }

  return (
    <svg
      width={width}
      height={height}
      className={className}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
    >
      {showFill && fillPath && <path d={fillPath} fill={fillColorValue} fillOpacity="0.2" />}
      <path
        d={pathData}
        fill="none"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
