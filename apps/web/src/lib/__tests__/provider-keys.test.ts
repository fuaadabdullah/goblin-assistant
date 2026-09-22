import { providerKeys } from '../provider-keys';

describe('providerKeys', () => {
  it('does not persist provider secrets in browser storage', () => {
    expect(providerKeys.get('openai')).toBeNull();

    providerKeys.set('openai', 'secret-1');
    providerKeys.set('anthropic', 'secret-2');

    expect(providerKeys.get('openai')).toBeNull();
    expect(providerKeys.get('anthropic')).toBeNull();

    providerKeys.remove('openai');

    expect(providerKeys.get('openai')).toBeNull();
    expect(providerKeys.get('anthropic')).toBeNull();
  });
});
