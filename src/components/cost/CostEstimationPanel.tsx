import { useState, useEffect } from 'react';
import { runtimeClient } from '@/api/api-client';
import './CostEstimationPanel.css';
import RaptorMiniPanel from '@/components/raptor/RaptorMiniPanel';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

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
  rateLimit?: {
    limit: number;
    remaining: number;
    reset?: number;
  };
}

// Cached rate table in USD per token (conservative defaults). Exported for tests.
export const RATE_CACHE: Record<string, Record<string, number>> = {
  openai: {
    // example rates per token (not necessarily accurate, conservative defaults)
    'gpt-4': 0.03, // $0.03 per token (very conservative)
    'gpt-3.5': 0.000002,
    demo: 0.00002,
  },
  anthropic: {
    'claude-2': 0.00008,
    demo: 0.00003,
  },
  default: {
    demo: 0.00002,
  },
};

export const getCachedRate = (provider?: string, model?: string): number => {
  if (!provider) return RATE_CACHE.default.demo;
  const p = provider.toLowerCase();
  const providerRates = (RATE_CACHE as any)[p];
  if (!providerRates) return RATE_CACHE.default.demo;
  if (model && providerRates[model]) return providerRates[model];
  // fallback to 'demo' or the first rate
  return providerRates['demo'] || Object.values(providerRates)[0] || RATE_CACHE.default.demo;
};

export const tokensFromChars = (chars: number): number => Math.max(Math.ceil(chars / 4), 1);

export const computeLocalCostEstimate = (
  orchestration: string,
  code: string,
  provider?: string,
  model?: string
): number => {
  // Conservative local estimate: estimate tokens based on characters then multiply by cached rate
  const totalChars = (orchestration?.length || 0) + (code?.length || 0);
  const tokens = tokensFromChars(totalChars);
  const tokenRate = getCachedRate(provider, model);
  return Math.max(tokens * tokenRate, 0.001); // Minimum $0.001
};

export const formatCost = (cost: number): string => {
  if (cost < 0.001) {
    return `$${(cost * 1000).toFixed(2)}m`; // Millicents
  } else if (cost < 0.01) {
    return `$${cost.toFixed(4)}`; // Micro dollars
  } else {
    return `$${cost.toFixed(4)}`;
  }
};

export const getCostColor = (cost: number): string => {
  if (cost < 0.001) return 'cost-low'; // Very cheap
  if (cost < 0.01) return 'cost-medium'; // Reasonable
  if (cost < 0.1) return 'cost-high'; // Expensive
  return 'cost-very-high'; // Very expensive
};

export const formatSummaryText = (estimate: CostEstimate | null): string => {
  if (!estimate) return '';
  // Pretty JSON summary with key data only for readability
  const summary = {
    totalCost: estimate.totalCost,
    currency: estimate.currency,
    steps: estimate.stepCosts.map(s => ({
      goblin: s.goblin,
      task: s.task,
      cost: s.estimatedCost,
      tokens: s.tokenEstimate,
    })),
  };
  return JSON.stringify(summary, null, 2);
};

export default function CostEstimationPanel({
  orchestrationText,
  codeInput = '',
  provider,
  model,
  onEstimatedCostChange,
}: Props) {
  const [estimate, setEstimate] = useState<CostEstimate | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [rateLimitInfo, setRateLimitInfo] = useState<CostEstimate['rateLimit'] | null>(null);
  const [streamLines, setStreamLines] = useState<string[]>([]);
  const [streaming, setStreaming] = useState<boolean>(false);
  const [showSummary, setShowSummary] = useState<boolean>(false);
  const [copyStatus, setCopyStatus] = useState<string | null>(null);

  useEffect(() => {
    if (orchestrationText.trim()) {
      calculateEstimate();
    } else {
      setEstimate(null);
      onEstimatedCostChange?.(0);
      setRateLimitInfo(null);
      setError(null);
      setStreamLines([]);
      setShowSummary(false);
    }
  }, [orchestrationText, codeInput, provider, model]);

  const copyFormattedSummary = async () => {
    const text = formatSummaryText(estimate);
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopyStatus('Copied');
      setTimeout(() => setCopyStatus(null), 1500);
    } catch (err) {
      setCopyStatus('Copy failed');
      setTimeout(() => setCopyStatus(null), 1500);
    }
  };

  const calculateEstimate = async () => {
    if (!orchestrationText.trim()) return;

    setLoading(true);
    setError(null);
    setStreaming(true);
    setStreamLines([]);
    setShowSummary(false);

    try {
      // Use the backend cost estimation
      // If the runtime client returns streaming progress, it should call back; here we check for a streaming API
      if ((runtimeClient as any).estimateCostStream) {
        // Use a streaming client if available
        await (runtimeClient as any).estimateCostStream(
          orchestrationText,
          codeInput,
          provider,
          model,
          (chunk: string) => {
            setStreamLines(prev => [...prev, chunk]);
          }
        );
        // Once streaming completes, call the non-streaming method for final estimate
        const backendEstimate = await runtimeClient.estimateCost(
          orchestrationText,
          codeInput,
          provider,
          model
        );
        const costEstimate: CostEstimate = {
          totalCost: backendEstimate.totalCost,
          stepCosts: backendEstimate.stepCosts,
          currency: backendEstimate.currency,
          rateLimit: backendEstimate.rateLimit,
        };

        setEstimate(costEstimate);
        setRateLimitInfo(backendEstimate.rateLimit ?? null);
        onEstimatedCostChange?.(backendEstimate.totalCost);
      } else {
        const backendEstimate = await runtimeClient.estimateCost(
          orchestrationText,
          codeInput,
          provider,
          model
        );

        const costEstimate: CostEstimate = {
          totalCost: backendEstimate.totalCost,
          stepCosts: backendEstimate.stepCosts,
          currency: backendEstimate.currency,
          rateLimit: backendEstimate.rateLimit,
        };

        setEstimate(costEstimate);
        setRateLimitInfo(backendEstimate.rateLimit ?? null);
        onEstimatedCostChange?.(backendEstimate.totalCost);
      }
    } catch (err: any) {
      // Log error via runtime client if available; otherwise set error for user
      if ((runtimeClient as any)?.log?.error) {
        (runtimeClient as any).log.error('Cost estimation error', err);
      }

      const message =
        (err && ((err.message as string) || (err.toString && err.toString()))) || 'API unavailable';
      if (/credential|auth|api key/i.test(message)) {
        setError('Pricing API credentials missing — using local cached rates');
      } else if (/429|rate limit|too many requests/i.test(message)) {
        const retry = err?.retryAfter ? ` Retry after ${err.retryAfter}s.` : '';
        setError(`Pricing API rate limit reached — using local cached rates.${retry}`);
      } else {
        setError('Using local estimate (API unavailable)');
      }

      // Fallback: compute local conservative estimate using cached rates
      const localEstimate = computeLocalCostEstimate(orchestrationText, codeInput, provider, model);
      const costEstimate: CostEstimate = {
        totalCost: localEstimate,
        stepCosts: [
          {
            stepId: 'local-1',
            goblin: 'Local Est',
            task: 'Local estimate',
            estimatedCost: localEstimate,
            tokenEstimate: tokensFromChars(orchestrationText.length + codeInput.length),
          },
        ],
        currency: 'USD',
      };

      setEstimate(costEstimate);
      onEstimatedCostChange?.(localEstimate);
    } finally {
      setLoading(false);
      setStreaming(false);
      setShowSummary(true);
      // Collapse streaming output into final formatted summary
      if (!streamLines.length && estimate) {
        // ensure the summary will be created from estimate
        setStreamLines([formatSummaryText(estimate)]);
      }
    }
  };

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

        {rateLimitInfo && (
          <div className="rate-limit">
            API Rate Limit: {rateLimitInfo.remaining}/{rateLimitInfo.limit}
          </div>
        )}

        {error && <div className="error">{error}</div>}

        {streaming && streamLines.length > 0 && (
          <div className="streaming-output">
            <h5>Streaming Output (live)</h5>
            <div className="stream-lines">
              {streamLines.map((line, i) => (
                <div key={`stream-${i}`} className="stream-line">
                  {line}
                </div>
              ))}
            </div>
          </div>
        )}

        {showSummary && estimate && (
          <div className="formatted-summary">
            <div className="summary-header">
              <h5>Formatted Summary</h5>
              <div className="summary-actions">
                <Button aria-label="Copy formatted docs" onClick={copyFormattedSummary} size="sm">
                  Copy formatted docs
                </Button>
                {copyStatus && <Badge className="copy-status">{copyStatus}</Badge>}
              </div>
            </div>
            <pre className="summary-pre">{formatSummaryText(estimate)}</pre>
          </div>
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
                * Estimates are approximate and based on typical token usage. Actual costs may vary
                based on actual response lengths and provider rates.
              </small>
            </div>
          </div>
        )}

        {/* Raptor Mini Demo in the UI for integration testing */}
        <div className="demo-raptor">
          <RaptorMiniPanel />
        </div>
      </CardContent>
    </Card>
  );
}
