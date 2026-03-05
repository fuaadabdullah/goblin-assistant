import type { CostEstimate } from '../../hooks/useCostEstimation';
import Button from '../ui/Button';

interface Props {
  estimate: CostEstimate | null;
  showSummary: boolean;
  copyStatus: string | null;
  onCopy: () => void;
}

export const CostSummary = ({ estimate, showSummary, copyStatus, onCopy }: Props) => {
  if (!showSummary || !estimate) return null;

  return (
    <div className="summary-panel">
      <div className="summary-header">
        <h4>Summary</h4>
        <Button variant="ghost" size="sm" onClick={onCopy}>
          {copyStatus || 'Copy summary'}
        </Button>
      </div>
      <div className="summary-content">
        <div>Estimated cost: ${estimate.estimatedCost.toFixed(4)}</div>
        <div>Estimated tokens: {estimate.estimatedTokens}</div>
      </div>
    </div>
  );
};
