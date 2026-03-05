
'use client';

// High contrast detection
export const highContrast = {
  // Check if high contrast mode is enabled
  isHighContrastMode(): boolean {
    if (typeof window === 'undefined') return false;

    // Check CSS media query
    const mq = window.matchMedia('(prefers-contrast: high)');
    if (mq.matches) return true;

    // Fallback: check computed styles
    const testElement = document.createElement('div');
    testElement.style.color = 'rgb(1,2,3)';
    testElement.style.position = 'absolute';
    testElement.style.visibility = 'hidden';
    document.body.appendChild(testElement);

    const computedColor = window.getComputedStyle(testElement).color;
    const isHighContrast = computedColor !== 'rgb(1, 2, 3)';

    document.body.removeChild(testElement);
    return isHighContrast;
  },

  // Detect contrast type
  getContrastType(): 'none' | 'low' | 'high' | 'max' | 'more' | 'less' {
    if (typeof window === 'undefined') return 'none';

    if (window.matchMedia('(prefers-contrast: high)').matches) return 'high';
    if (window.matchMedia('(prefers-contrast: more)').matches) return 'more';
    if (window.matchMedia('(prefers-contrast: less)').matches) return 'less';
    return 'none';
  },
};
