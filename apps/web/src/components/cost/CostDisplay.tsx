import type { CostEstimate } from '../../hooks/useCostEstimation';
import { formatCost } from '@/utils/format-cost';

interface Props {
  estimate: CostEstimate;
}

export const CostDisplay = ({ estimate }: Props) => {
  return (
    <div className="estimate-results">
      <div className="estimate-row">
        <span>Total Estimated Cost</span>
        <strong>{formatCost(estimate.estimatedCost, { mode: 'per-message' })}</strong>
      </div>
      <div className="estimate-row">
        <span>Estimated Tokens</span>
        <strong>{estimate.estimatedTokens}</strong>
      </div>
      {estimate.breakdown && estimate.breakdown.length > 0 && (
        <div className="estimate-breakdown">
          {estimate.breakdown.map(item => (
            <div key={item.label} className="estimate-row">
              <span>{item.label}</span>
              <span>
                {formatCost(item.cost, { mode: 'per-message' })} · {item.tokens} tokens
              </span>
            </div>
          ))}
        </div>
      )}
      <div className="estimate-disclaimer">
        <small>Costs are estimates and may vary based on provider billing.</small>
      </div>
    </div>
  );
};
