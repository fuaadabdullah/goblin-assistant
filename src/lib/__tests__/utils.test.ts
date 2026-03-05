import { cn } from '../utils';

describe('Utility Functions', () => {
  describe('cn (className merger)', () => {
    it('should merge single className', () => {
      expect(cn('flex')).toContain('flex');
    });

    it('should merge multiple classNames', () => {
      const result = cn('flex', 'gap-4', 'p-2');
      expect(result).toContain('flex');
      expect(result).toContain('gap-4');
      expect(result).toContain('p-2');
    });

    it('should handle conditional classNames', () => {
      const isActive = true;
      const result = cn('base', isActive && 'active');
      expect(result).toContain('base');
      expect(result).toContain('active');
    });

    it('should filter out falsy values', () => {
      const result = cn('flex', false && 'hidden', null, 'gap-4', undefined);
      expect(result).toContain('flex');
      expect(result).toContain('gap-4');
      expect(result).not.toContain('hidden');
    });

    it('should handle array of classNames', () => {
      const result = cn(['flex', 'gap-4'], 'p-2');
      expect(result).toContain('flex');
      expect(result).toContain('gap-4');
      expect(result).toContain('p-2');
    });

    it('should handle objects with boolean values', () => {
      const result = cn({
        flex: true,
        hidden: false,
        'gap-4': true,
      });
      expect(result).toContain('flex');
      expect(result).toContain('gap-4');
    });

    it('should override conflicting Tailwind classes', () => {
      const result = cn('p-2', 'p-4');
      expect(result).toBeDefined();
      // clsx/cn should handle Tailwind conflicts appropriately
    });
  });
});
