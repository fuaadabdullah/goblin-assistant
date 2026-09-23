import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { normalizeProviderId, PROVIDER_ID_ALIASES } from '@/lib/providers/normalizeProvider';

export interface ProviderSelectionState {
  selectedProvider: string;
  selectedModel: string;
  setSelectedProvider: (provider: string) => void;
  setSelectedModel: (model: string) => void;
}

type PersistedProviderSelection = Pick<
  ProviderSelectionState,
  'selectedProvider' | 'selectedModel'
>;

const STORAGE_KEY = 'goblin-provider-storage';
const LEGACY_PROVIDER_KEY = 'selectedProvider';
const LEGACY_MODEL_KEY = 'selectedModel';

export const useProviderStore = create<ProviderSelectionState>()(
  persist<ProviderSelectionState, [], [], PersistedProviderSelection>(
    (set) => ({
      selectedProvider: '',
      selectedModel: '',

      setSelectedProvider: (provider: string) => {
        const canonical = normalizeProviderId(provider, PROVIDER_ID_ALIASES);
        set((state) => ({
          selectedProvider: canonical,
          selectedModel: state.selectedProvider === canonical ? state.selectedModel : '',
        }));
      },

      setSelectedModel: (model: string) => set({ selectedModel: model }),
    }),
    {
      name: STORAGE_KEY,
      partialize: (state) => ({
        selectedProvider: state.selectedProvider,
        selectedModel: state.selectedModel,
      }),
      skipHydration: true,
    }
  )
);

/**
 * One-time migration from the pre-zustand `useProviderSelection` localStorage keys.
 * Clears the legacy keys once the selection has been moved into the persisted store.
 */
export function migrateLegacyProviderSelection(): void {
  if (typeof window === 'undefined') return;

  try {
    const legacyProvider = window.localStorage.getItem(LEGACY_PROVIDER_KEY);
    const legacyModel = window.localStorage.getItem(LEGACY_MODEL_KEY);

    if (legacyProvider !== null || legacyModel !== null) {
      const state = useProviderStore.getState();
      if (!state.selectedProvider && !state.selectedModel) {
        useProviderStore.setState({
          selectedProvider: normalizeProviderId(legacyProvider ?? '', PROVIDER_ID_ALIASES),
          selectedModel: legacyModel ?? '',
        });
      }
      window.localStorage.removeItem(LEGACY_PROVIDER_KEY);
      window.localStorage.removeItem(LEGACY_MODEL_KEY);
    }
  } catch {
    // Storage unavailable (SSR, privacy mode, quota): ignore.
  }
}
