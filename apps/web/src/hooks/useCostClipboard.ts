import { useCallback, useState } from 'react';
import type { CostEstimate } from './useCostEstimation';
import { formatCost } from '@/utils/format-cost';

export const useCostClipboard = () => {
  const [copyStatus, setCopyStatus] = useState<string | null>(null);

  const copyFormattedSummary = useCallback(async (estimate: CostEstimate | null) => {
    if (!estimate) return;

    const summary = `Estimated cost: ${formatCost(estimate.estimatedCost, { mode: 'per-message' })}\nEstimated tokens: ${estimate.estimatedTokens}`;

    try {
      await navigator.clipboard.writeText(summary);
      setCopyStatus('Copied');
    } catch (error) {
      setCopyStatus('Copy failed');
    } finally {
      setTimeout(() => setCopyStatus(null), 1500);
    }
  }, []);

  return {
    copyStatus,
    copyFormattedSummary,
  };
};
