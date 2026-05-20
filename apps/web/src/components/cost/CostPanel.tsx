import type { CostSummary } from '@/types/api';
import { formatCost } from '@/utils/format-cost';

interface Props {
  costSummary?: CostSummary | null;
}

export default function CostPanel({ costSummary }: Props) {
  if (!costSummary) return null;

  return (
    <div className="cost-panel">
      <h3>Cost Summary</h3>
      <div>
        <strong>Total:</strong> {formatCost(costSummary.total_cost, { mode: 'summary' })}
      </div>
      <div>
        <strong>By Provider:</strong>
        <ul>
          {Object.entries(costSummary.cost_by_provider).map(([p, c]) => (
            <li key={p}>
              {p}: {formatCost(Number(c), { mode: 'summary' })}
            </li>
          ))}
        </ul>
      </div>
      <div>
        <strong>By Model:</strong>
        <ul>
          {Object.entries(costSummary.cost_by_model).map(([m, c]) => (
            <li key={m}>
              {m}: {formatCost(Number(c), { mode: 'summary' })}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
