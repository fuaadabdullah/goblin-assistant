import { useCallback, useState } from 'react';
import type { CostEstimate } from './useCostEstimation';

interface Options {
  estimate: CostEstimate | null;
}

export const useCostStreaming = ({ estimate }: Options) => {
  const [streamLines, setStreamLines] = useState<string[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [showSummary, setShowSummary] = useState(false);

  const startStreaming = useCallback(
    (orchestrationText: string, codeInput: string, provider?: string, model?: string) => {
      setStreaming(true);
      setShowSummary(false);
      setStreamLines([
        'Analyzing orchestration...',
        `Provider: ${provider || 'auto'}`,
        `Model: ${model || 'auto'}`,
        `Code length: ${codeInput.length} chars`,
        `Instruction length: ${orchestrationText.length} chars`,
      ]);

      setTimeout(() => {
        setStreaming(false);
        setShowSummary(true);
      }, 300);
    },
    []
  );

  const resetStreaming = useCallback(() => {
    setStreaming(false);
    setShowSummary(false);
    setStreamLines([]);
  }, []);

  return {
    streamLines,
    streaming,
    showSummary: showSummary || Boolean(estimate),
    startStreaming,
    resetStreaming,
  };
};
