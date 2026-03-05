import { useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import RaptorMiniPanel from '../raptor/RaptorMiniPanel';
import { useCostEstimation } from '../../hooks/useCostEstimation';
import { useCostStreaming } from '../../hooks/useCostStreaming';
import { useCostClipboard } from '../../hooks/useCostClipboard';
import { CostDisplay } from './CostDisplay';
import { CostSummary } from './CostSummary';
import { CostStreaming } from './CostStreaming';
import { CostRateLimit } from './CostRateLimit';
import './CostEstimationPanel.css';

interface CostEstimationPanelProps {
  orchestrationText: string;
  codeInput?: string;
  provider?: string;
  model?: string;
  onEstimatedCostChange?: (cost: number) => void;
}

export default function CostEstimationPanel({
  orchestrationText,
  codeInput = '',
  provider,
  model,
  onEstimatedCostChange,
}: CostEstimationPanelProps) {
  // Use custom hooks for state management
  const { estimate, loading, error, rateLimitInfo } = useCostEstimation({
    orchestrationText,
    codeInput,
    provider,
    model,
    onEstimatedCostChange,
  });

  const { streamLines, streaming, showSummary, startStreaming, resetStreaming } = useCostStreaming({
    estimate,
  });

  const { copyStatus, copyFormattedSummary } = useCostClipboard();

  // Start streaming when estimation begins
  useEffect(() => {
    if (orchestrationText.trim() && !estimate) {
      startStreaming(orchestrationText, codeInput, provider, model);
    } else if (!orchestrationText.trim()) {
      resetStreaming();
    }
  }, [orchestrationText, codeInput, provider, model, estimate]);

  if (!orchestrationText.trim()) {
    return (
      <Card className="cost-estimation-panel">
        <CardHeader>
          <CardTitle>Cost Estimation</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="no-estimate">Enter an orchestration command to see cost estimates</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="cost-estimation-panel">
      <CardHeader>
        <CardTitle>Cost Estimation</CardTitle>
      </CardHeader>
      <CardContent>
        {loading && <div className="loading">Calculating cost estimates...</div>}

        <CostRateLimit rateLimitInfo={rateLimitInfo} />

        {error && <div className="error">{error}</div>}

        <CostStreaming streaming={streaming} streamLines={streamLines} />

        <CostSummary
          estimate={estimate}
          showSummary={showSummary}
          copyStatus={copyStatus}
          onCopy={() => copyFormattedSummary(estimate)}
        />

        {estimate && <CostDisplay estimate={estimate} />}

        {/* Raptor Mini Demo in the UI for integration testing */}
        <div className="demo-raptor">
          <RaptorMiniPanel />
        </div>
      </CardContent>
    </Card>
  );
}
