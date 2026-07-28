const KEY_PREFIX = 'goblin_provider_key:';

const storeKey = (provider: string): string => `${KEY_PREFIX}${provider}`;

export const providerKeys = {
  get(provider: string): string | null {
    if (typeof window === 'undefined') return null;
    try {
      return window.localStorage.getItem(storeKey(provider));
    } catch {
      return null;
    }
  },

  set(provider: string, key: string): void {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(storeKey(provider), key);
    } catch {
      // QuotaExceededError or similar — silently drop
    }
  },

  remove(provider: string): void {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.removeItem(storeKey(provider));
    } catch {
      // ignore
    }
  },
};
