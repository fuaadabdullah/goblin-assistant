import { formatTitle, sampleHelper } from '../modular/utils';

describe('modular utils', () => {
  describe('formatTitle', () => {
    it('trims whitespace', () => {
      expect(formatTitle('  Hello  ')).toBe('Hello');
    });

    it('collapses multiple spaces', () => {
      expect(formatTitle('Hello    World')).toBe('Hello World');
    });

    it('removes special characters', () => {
      expect(formatTitle('Hello!@#World')).toBe('HelloWorld');
    });

    it('preserves hyphens and word characters', () => {
      expect(formatTitle('Hello-World Test')).toBe('Hello-World Test');
    });

    it('handles empty string', () => {
      expect(formatTitle('')).toBe('');
    });

    it('handles string with only special chars', () => {
      expect(formatTitle('@#$%')).toBe('');
    });
  });

  describe('sampleHelper', () => {
    it('returns the number for positive integers', () => {
      expect(sampleHelper(5)).toBe(5);
    });

    it('returns 0 for negative numbers', () => {
      expect(sampleHelper(-3)).toBe(0);
    });

    it('returns 0 for 0', () => {
      expect(sampleHelper(0)).toBe(0);
    });

    it('floors non-integer values', () => {
      expect(sampleHelper(3.7)).toBe(3);
    });

    it('returns 0 for negative non-integer values', () => {
      expect(sampleHelper(-2.5)).toBe(0);
    });
  });
});
