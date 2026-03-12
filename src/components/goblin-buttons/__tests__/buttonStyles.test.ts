import { baseButtonStyles, getButtonClasses } from '../buttonStyles';
import type { ButtonStyleVariant } from '../buttonStyles';

describe('buttonStyles', () => {
  it('baseButtonStyles is a non-empty string', () => {
    expect(typeof baseButtonStyles).toBe('string');
    expect(baseButtonStyles.length).toBeGreaterThan(0);
  });

  it('baseButtonStyles includes core classes', () => {
    expect(baseButtonStyles).toContain('rounded-md');
    expect(baseButtonStyles).toContain('transition-all');
    expect(baseButtonStyles).toContain('disabled:opacity-50');
  });

  const variants: ButtonStyleVariant[] = ['primary', 'cta', 'danger', 'ghost', 'icon-ghost', 'icon-primary', 'icon-danger'];

  it.each(variants)('getButtonClasses returns a string for variant "%s"', (variant) => {
    const classes = getButtonClasses(variant);
    expect(typeof classes).toBe('string');
    expect(classes.length).toBeGreaterThan(0);
  });

  it('primary variant includes bg-primary', () => {
    expect(getButtonClasses('primary')).toContain('bg-primary');
  });

  it('cta variant includes bg-cta', () => {
    expect(getButtonClasses('cta')).toContain('bg-cta');
  });

  it('danger variant includes bg-danger', () => {
    expect(getButtonClasses('danger')).toContain('bg-danger');
  });

  it('ghost variant includes border', () => {
    expect(getButtonClasses('ghost')).toContain('border');
  });

  it('appends custom className', () => {
    const classes = getButtonClasses('primary', 'my-custom');
    expect(classes).toContain('my-custom');
  });

  it('handles empty className gracefully', () => {
    const classes = getButtonClasses('primary', '');
    expect(classes).toContain('bg-primary');
  });

  it('handles unknown variant via default case', () => {
    const classes = getButtonClasses('unknown' as ButtonStyleVariant);
    expect(classes).toContain(baseButtonStyles);
  });
});
