import { useMemo } from 'react';
import { CHAT_QUICK_PROMPTS } from '../../../content/brand';
import { useProvider } from '../../../contexts/ProviderContext';
import type { QuickPrompt } from '../types';

export interface QuickActionsState {
  quickPrompts: QuickPrompt[];
  selectedProvider?: string;
  selectedModel?: string;
}

/**
 * Manages quick prompts and provider/model selection
 */
export const useQuickActions = (): QuickActionsState => {
  const { selectedProvider, selectedModel } = useProvider();

  const quickPrompts = useMemo<QuickPrompt[]>(
    () => CHAT_QUICK_PROMPTS.map((item) => ({ label: item.label, prompt: item.prompt })),
    []
  );

  return {
    quickPrompts,
    selectedProvider: selectedProvider || undefined,
    selectedModel: selectedModel || undefined,
  };
};
