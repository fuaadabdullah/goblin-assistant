import Card from './Card';

export interface StatCardProps {
  label: string;
  value: string | number;
  hint?: string;
  className?: string;
}

/**
 * StatCard — compact KPI tile with left-aligned label and right-aligned value.
 * Accessible by default, with a minimum hit size and clear focus ring.
 */
export default function StatCard({ label, value, hint, className = '' }: StatCardProps) {
  return (
    <Card
      padded
      bordered
      radius="md"
      className={`min-h-[64px] ${className}`}
      role="group"
      aria-label={`${label} ${typeof value === 'number' ? value.toString() : value}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted">{label}</span>
        <span className="text-2xl font-bold text-text">
          {typeof value === 'number' ? value : value}
        </span>
      </div>
      {hint && <div className="mt-1 text-[11px] text-muted">{hint}</div>}
    </Card>
  );
}
