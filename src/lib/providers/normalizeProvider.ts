/**
 * Shared provider ID normalization utilities.
 */

export const PROVIDER_ID_ALIASES: Record<string, string> = {
  'ollama-gcp': 'ollama_gcp',
  'llamacpp-gcp': 'llamacpp_gcp',
  'azure-openai': 'azure_openai',
  azure: 'azure_openai',
  google: 'gemini',
  alibaba: 'aliyun',
  'ali-baba': 'aliyun',
  'aliyun-model-server': 'aliyun',
};

export function normalizeProviderId(
  value: string | null | undefined,
  aliases: Record<string, string> = PROVIDER_ID_ALIASES
): string {
  const raw = (value || '').trim().toLowerCase();
  if (!raw) return '';

  const aliasResolved = aliases[raw] || raw;
  return aliasResolved.replace(/[-\s]+/g, '_');
}

export function providerRateLookupKeys(value: string | null | undefined): string[] {
  const normalized = normalizeProviderId(value);
  if (!normalized) return [];

  const withHyphen = normalized.replace(/_/g, '-');
  return withHyphen === normalized ? [normalized] : [normalized, withHyphen];
}
