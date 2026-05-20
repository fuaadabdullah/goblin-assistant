import { generateClientId, generateConversationId, generateMessageId } from '../id-generation';

describe('id-generation', () => {
  it('generateClientId returns a string', () => {
    const id = generateClientId();
    expect(typeof id).toBe('string');
    expect(id.length).toBeGreaterThan(0);
  });

  it('generateClientId produces unique IDs', () => {
    const ids = new Set(Array.from({ length: 50 }, () => generateClientId()));
    expect(ids.size).toBe(50);
  });

  it('generateClientId uses fallback when crypto.randomUUID is unavailable', () => {
    const original = globalThis.crypto;
    Object.defineProperty(globalThis, 'crypto', { value: undefined, configurable: true });
    try {
      const id = generateClientId('test');
      expect(id).toMatch(/^test-\d+-[0-9a-f]+$/);
    } finally {
      Object.defineProperty(globalThis, 'crypto', { value: original, configurable: true });
    }
  });

  it('generateConversationId returns a string', () => {
    const id = generateConversationId();
    expect(typeof id).toBe('string');
    expect(id.length).toBeGreaterThan(0);
  });

  it('generateMessageId returns a string', () => {
    const id = generateMessageId();
    expect(typeof id).toBe('string');
    expect(id.length).toBeGreaterThan(0);
  });
});
