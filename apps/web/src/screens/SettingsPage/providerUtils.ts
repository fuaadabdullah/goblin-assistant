import type { ProviderDisplay } from './types';
import { LOCAL_PROVIDER_HINTS, CLOUD_PROVIDER_HINTS } from './constants';

export const normalizeProviderName = (name: string) => name.toLowerCase().replace(/\s+/g, '_');

export const providerMatchesSearch = (provider: ProviderDisplay, query: string) => {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) return true;
  return [
    provider.name,
    provider.normalizedName,
    provider.env_var ?? '',
    provider.base_url ?? '',
    ...provider.models,
  ]
    .join(' ')
    .toLowerCase()
    .includes(normalizedQuery);
};

export const isLocalProvider = (provider: ProviderDisplay) =>
  LOCAL_PROVIDER_HINTS.some((hint) => provider.normalizedName.includes(hint));

export const isCloudProvider = (provider: ProviderDisplay) =>
  CLOUD_PROVIDER_HINTS.some((hint) => provider.normalizedName.includes(hint));
