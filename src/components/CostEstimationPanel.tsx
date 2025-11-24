import { useState, useEffect } from 'react';
import { runtimeClient } from '../api/tauri-client';
import './CostEstimationPanel.css';

interface Props {
  orchestrationText: string;
  codeInput?: string;
  provider?: string;
  model?: string;
  onEstimatedCostChange?: (cost: number) => void;
}

interface CostEstimate {
  totalCost: number;
  stepCosts: Array<{
    stepId: string;
    goblin: string;
    task: string;
    estimatedCost: number;
    tokenEstimate: number;
  }>;
  currency: string;
}

export default function CostEstimationPanel({
  orchestrationText,
  codeInput = '',
  provider,
  model,
  onEstimatedCostChange
}: Props) {
  const [estimate, setEstimate] = useState<CostEstimate | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (orchestrationText.trim()) {
      calculateEstimate();
    } else {
      setEstimate(null);
      onEstimatedCostChange?.(0);
    }
  }, [orchestrationText, codeInput, provider, model]);

  const calculateEstimate = async () => {
    if (!orchestrationText.trim()) return;

    setLoading(true);
    setError(null);

    try {
      // Use the backend cost estimation
      const estimate = await runtimeClient.estimateCost(orchestrationText, codeInput, provider);

      const costEstimate: CostEstimate = {
        totalCost: estimate.totalCost,
        stepCosts: estimate.stepCosts,
        currency: estimate.currency
      };

      setEstimate(costEstimate);
      onEstimatedCostChange?.(estimate.totalCost);

    } catch (err) {
      console.error('Cost estimation error:', err);
      setError('Failed to calculate cost estimate');
      setEstimate(null);
      onEstimatedCostChange?.(0);
    } finally {
      setLoading(false);
    }
  };

  const formatCost = (cost: number): string => {
    if (cost < 0.001) {
      return `$${(cost * 1000).toFixed(2)}m`; // Millicents
    } else if (cost < 0.01) {
      return `$${cost.toFixed(4)}`; // Micro dollars
    } else {
      return `$${cost.toFixed(4)}`;
    }
  };

  const getCostColor = (cost: number): string => {
    if (cost < 0.001) return 'cost-low';       // Very cheap
    if (cost < 0.01) return 'cost-medium';     // Reasonable
    if (cost < 0.1) return 'cost-high';        // Expensive
    return 'cost-very-high';                   // Very expensive
  };

  if (!orchestrationText.trim()) {
    return (
      <div className="cost-estimation-panel">
        <h4>Cost Estimation</h4>
        <p className="no-estimate">Enter an orchestration command to see cost estimates</p>
      </div>
    );
  }

  return (
    <div className="cost-estimation-panel">
      <h4>Cost Estimation</h4>

      {loading && (
        <div className="loading">Calculating cost estimates...</div>
      )}

      {error && (
        <div className="error">{error}</div>
      )}

      {estimate && !loading && (
        <div className="estimate-results">
          <div className="total-cost">
            <span className="label">Total Estimated Cost:</span>
            <span className={`value ${getCostColor(estimate.totalCost)}`}>
              {formatCost(estimate.totalCost)}
            </span>
          </div>

          <div className="cost-breakdown">
            <h5>Step-by-Step Breakdown</h5>
            <div className="step-costs">
              {estimate.stepCosts.map((step, index) => (
                <div key={step.stepId} className="step-cost-item">
                  <div className="step-info">
                    <span className="step-number">{index + 1}.</span>
                    <span className="step-goblin">{step.goblin}</span>
                    <span className="step-task" title={step.task}>
                      {step.task.length > 30 ? `${step.task.substring(0, 30)}...` : step.task}
                    </span>
                  </div>
                  <div className="step-cost-details">
                    <span className="tokens">~{step.tokenEstimate} tokens</span>
                    <span className={`cost ${getCostColor(step.estimatedCost)}`}>
                      {formatCost(step.estimatedCost)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="estimate-disclaimer">
            <small>
              * Estimates are approximate and based on typical token usage.
              Actual costs may vary based on actual response lengths and provider rates.
            </small>
          </div>
        </div>
      )}
    </div>
  );
}
