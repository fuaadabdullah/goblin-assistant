// Stub implementation for useSettings hook
export interface ProviderConfig {
  id: string;
  name: string;
  type: string;
  status: string;
  enabled: boolean;
  priority?: number;
  models?: string[];
  base_url?: string;
  api_key?: string;
}

export function useProviderSettings() {
  return {
    settings: [],
    isLoading: false,
    error: null,
    refetch: () => {},
  };
}

export function useSettings() {
  return {
    settings: {},
    isLoading: false,
    error: null,
  };
}
