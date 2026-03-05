
'use client';

// Text scaling utilities
export const textScaling = {
  // Check if text is scaled
  isTextScaled(): boolean {
    if (typeof window === 'undefined') return false;

    const testElement = document.createElement('div');
    testElement.style.fontSize = '100px';
    testElement.style.position = 'absolute';
    testElement.style.visibility = 'hidden';
    document.body.appendChild(testElement);

    const computedStyle = window.getComputedStyle(testElement);
    const isScaled = computedStyle.fontSize !== '100px';

    document.body.removeChild(testElement);
    return isScaled;
  },

  // Get text scale factor
  getTextScaleFactor(): number {
    if (typeof window === 'undefined') return 1;

    const testElement = document.createElement('div');
    testElement.style.fontSize = '100px';
    testElement.style.position = 'absolute';
    testElement.style.visibility = 'hidden';
    document.body.appendChild(testElement);

    const computedStyle = window.getComputedStyle(testElement);
    const scaleFactor = parseFloat(computedStyle.fontSize) / 100;

    document.body.removeChild(testElement);
    return scaleFactor;
  },
};
