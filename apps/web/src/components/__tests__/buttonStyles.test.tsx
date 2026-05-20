import { getButtonClasses } from '../goblin-buttons/buttonStyles';

describe('buttonStyles', () => {
  describe('getButtonClasses', () => {
    it('returns primary variant classes', () => {
      const result = getButtonClasses('primary');
      expect(result).toContain('bg-primary');
      expect(result).toContain('px-4');
      expect(result).toContain('py-2');
    });

    it('returns cta variant classes', () => {
      const result = getButtonClasses('cta');
      expect(result).toContain('bg-cta');
      expect(result).toContain('px-4');
      expect(result).toContain('py-2');
    });

    it('returns danger variant classes', () => {
      const result = getButtonClasses('danger');
      expect(result).toContain('bg-danger');
    });

    it('returns ghost variant classes', () => {
      const result = getButtonClasses('ghost');
      expect(result).toContain('border');
      expect(result).toContain('border-border');
    });

    it('returns icon-ghost variant classes', () => {
      const result = getButtonClasses('icon-ghost');
      expect(result).toContain('p-2');
      expect(result).toContain('hover:scale-110');
    });

    it('returns icon-primary variant classes', () => {
      const result = getButtonClasses('icon-primary');
      expect(result).toContain('p-2');
      expect(result).toContain('hover:bg-primary/15');
    });

    it('returns icon-danger variant classes', () => {
      const result = getButtonClasses('icon-danger');
      expect(result).toContain('p-2');
      expect(result).toContain('hover:bg-danger/15');
    });

    it('appends custom className', () => {
      const result = getButtonClasses('primary', 'my-custom-class');
      expect(result).toContain('my-custom-class');
    });

    it('includes base styles for non-icon variants', () => {
      const result = getButtonClasses('primary');
      expect(result).toContain('rounded-md');
      expect(result).toContain('text-sm');
      expect(result).toContain('font-semibold');
    });

    it('returns base styles for unknown variant', () => {
      const result = getButtonClasses('unknown-variant' as any);
      expect(result).toContain('rounded-md');
    });
  });
});
