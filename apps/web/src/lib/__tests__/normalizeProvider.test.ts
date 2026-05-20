import {
  normalizeProviderId,
  providerRateLookupKeys,
  PROVIDER_ID_ALIASES,
} from '../providers/normalizeProvider';

describe('normalizeProviderId', () => {
  test('normalizes case, whitespace, and separators', () => {
    expect(normalizeProviderId('  Azure-OpenAI  ')).toBe('azure_openai');
    expect(normalizeProviderId('silicone flow')).toBe('silicone_flow');
    expect(normalizeProviderId('DeepSeek')).toBe('deepseek');
  });

  test('returns empty string for nullish/empty values', () => {
    expect(normalizeProviderId(undefined)).toBe('');
    expect(normalizeProviderId(null)).toBe('');
    expect(normalizeProviderId('   ')).toBe('');
  });

  test('applies alias map when provided', () => {
    expect(normalizeProviderId('azure', PROVIDER_ID_ALIASES)).toBe('azure_openai');
    expect(normalizeProviderId('alibaba', PROVIDER_ID_ALIASES)).toBe('aliyun');
    expect(normalizeProviderId('ali-baba', PROVIDER_ID_ALIASES)).toBe('aliyun');
  });
});

describe('providerRateLookupKeys', () => {
  test('returns underscore and hyphen forms where applicable', () => {
    expect(providerRateLookupKeys('open_router')).toEqual(['open_router', 'open-router']);
    expect(providerRateLookupKeys('open-router')).toEqual(['open_router', 'open-router']);
  });

  test('returns single key when hyphen and normalized forms are identical', () => {
    expect(providerRateLookupKeys('openai')).toEqual(['openai']);
  });

  test('returns empty list for empty input', () => {
    expect(providerRateLookupKeys(undefined)).toEqual([]);
    expect(providerRateLookupKeys('')).toEqual([]);
  });
});
