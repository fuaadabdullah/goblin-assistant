import { useMemo, useState } from 'react';
import { CHAT_QUICK_PROMPTS } from '../../../content/brand';
import { useProviderStore } from '@/store/providerStore';
import type { Mode, QuickPrompt } from '../types';

export interface QuickActionsState {
  quickPrompts: QuickPrompt[];
  selectedProvider?: string | undefined;
  selectedModel?: string | undefined;
  selectedMode: Mode;
  setSelectedMode: (mode: Mode) => void;
}

/**
 * Manages quick prompts, provider/model selection, and chat mode
 */
export const useQuickActions = (): QuickActionsState => {
  const selectedProvider = useProviderStore((state) => state.selectedProvider);
  const selectedModel = useProviderStore((state) => state.selectedModel);
  const [selectedMode, setSelectedMode] = useState<Mode>('all');

  const quickPrompts = useMemo<QuickPrompt[]>(
    () => CHAT_QUICK_PROMPTS.map((item) => ({ label: item.label, prompt: item.prompt })),
    []
  );

  return {
    quickPrompts,
    selectedProvider: selectedProvider || undefined,
    selectedModel: selectedModel || undefined,
    selectedMode,
    setSelectedMode,
  };
};
