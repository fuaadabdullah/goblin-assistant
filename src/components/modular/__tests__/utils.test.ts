import { formatTitle, sampleHelper } from '../utils';

describe('modular/utils', () => {
  describe('formatTitle', () => {
    it('trims whitespace', () => {
      expect(formatTitle('  hello  ')).toBe('hello');
    });

    it('collapses multiple spaces', () => {
      expect(formatTitle('hello   world')).toBe('hello world');
    });

    it('removes special characters', () => {
      expect(formatTitle('hello! @world#')).toBe('hello world');
    });

    it('preserves hyphens', () => {
      expect(formatTitle('my-title')).toBe('my-title');
    });

    it('handles empty string', () => {
      expect(formatTitle('')).toBe('');
    });

    it('handles string with only special chars', () => {
      expect(formatTitle('!@#$%')).toBe('');
    });
  });

  describe('sampleHelper', () => {
    it('floors positive numbers', () => {
      expect(sampleHelper(3.7)).toBe(3);
    });

    it('returns 0 for negative numbers', () => {
      expect(sampleHelper(-5)).toBe(0);
    });

    it('returns 0 for zero', () => {
      expect(sampleHelper(0)).toBe(0);
    });

    it('handles integers unchanged (positive)', () => {
      expect(sampleHelper(10)).toBe(10);
    });
  });
});
