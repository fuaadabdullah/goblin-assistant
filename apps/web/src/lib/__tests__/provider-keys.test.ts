import { providerKeys } from '../provider-keys';

describe('providerKeys', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('stores, reads, and removes keys per provider', () => {
    expect(providerKeys.get('openai')).toBeNull();

    providerKeys.set('openai', 'secret-1');
    providerKeys.set('anthropic', 'secret-2');

    expect(providerKeys.get('openai')).toBe('secret-1');
    expect(providerKeys.get('anthropic')).toBe('secret-2');

    providerKeys.remove('openai');

    expect(providerKeys.get('openai')).toBeNull();
    expect(providerKeys.get('anthropic')).toBe('secret-2');
  });
});
