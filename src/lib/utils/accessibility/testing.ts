
'use client';

// Accessibility testing utilities
export const a11yTest = {
  // Check color contrast
  testColorContrast(element: HTMLElement): { ratio: number; compliant: boolean } {
    if (typeof window === 'undefined') return { ratio: 0, compliant: false };

    const styles = window.getComputedStyle(element);
    const backgroundColor = styles.backgroundColor;
    const color = styles.color;

    // Calculate contrast ratio manually
    const getLuminance = (color: string): number => {
      const rgb = color.match(/\d+/g);
      if (!rgb) return 0;
      const [r, g, b] = rgb.map(Number);
      const [rs, gs, bs] = [r, g, b].map((c) => {
        c = c / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
    };

    const getContrastRatio = (color1: string, color2: string): number => {
      const lum1 = getLuminance(color1);
      const lum2 = getLuminance(color2);
      const brightest = Math.max(lum1, lum2);
      const darkest = Math.min(lum1, lum2);
      return (brightest + 0.05) / (darkest + 0.05);
    };

    const ratio = getContrastRatio(color, backgroundColor);
    const compliant = ratio >= 4.5; // WCAG AA normal text requirement

    return { ratio, compliant };
  },

  // Check focus order
  testFocusOrder(container: HTMLElement): boolean {
    if (typeof window === 'undefined') return false;

    const focusableElements = Array.from(
      container.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
    ) as HTMLElement[];

    let lastTabIndex = -1;
    for (const element of focusableElements) {
      const tabIndex = parseInt(element.getAttribute('tabindex') || '0', 10);
      if (tabIndex < lastTabIndex && tabIndex > 0) {
        console.warn('Invalid tab order detected');
        return false;
      }
      lastTabIndex = tabIndex;
    }

    return true;
  },

  // Check ARIA attributes
  testAriaAttributes(element: HTMLElement): string[] {
    if (typeof window === 'undefined') return [];

    const issues: string[] = [];
    const role = element.getAttribute('role');

    // Check for required attributes based on role
    if (role === 'button' && !element.hasAttribute('aria-label')) {
      issues.push('Button missing aria-label');
    }

    if (role === 'dialog' && !element.hasAttribute('aria-labelledby')) {
      issues.push('Dialog missing aria-labelledby');
    }

    if (role === 'tablist') {
      const tabs = element.querySelectorAll('[role="tab"]');
      tabs.forEach((tab) => {
        if (!tab.hasAttribute('aria-controls')) {
          issues.push('Tab missing aria-controls');
        }
      });
    }

    return issues;
  },
};
