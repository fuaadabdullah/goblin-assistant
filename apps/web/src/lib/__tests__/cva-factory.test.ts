import { getBaseComponentClasses } from '../cva-factory';

describe('cva-factory', () => {
  it('getBaseComponentClasses returns a string', () => {
    const classes = getBaseComponentClasses();
    expect(typeof classes).toBe('string');
    expect(classes.length).toBeGreaterThan(0);
  });

  it('includes focus-visible ring classes', () => {
    const classes = getBaseComponentClasses();
    expect(classes).toContain('focus-visible:outline');
    expect(classes).toContain('focus-visible:outline-2');
    expect(classes).toContain('focus-visible:outline-primary');
  });

  it('includes disabled state classes', () => {
    const classes = getBaseComponentClasses();
    expect(classes).toContain('disabled:opacity-50');
    expect(classes).toContain('disabled:cursor-not-allowed');
  });

  it('includes transition classes', () => {
    const classes = getBaseComponentClasses();
    expect(classes).toContain('transition-all');
    expect(classes).toContain('duration-150');
  });
});
