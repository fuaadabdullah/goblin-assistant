
'use client';

// Screen reader utilities
export const screenReader = {
  // Announce message
  announce(message: string, priority: 'polite' | 'assertive' = 'polite'): void {
    if (typeof window === 'undefined') return;

    const liveRegion = document.createElement('div');
    liveRegion.setAttribute('aria-live', priority);
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.style.position = 'absolute';
    liveRegion.style.left = '-10000px';
    liveRegion.style.width = '1px';
    liveRegion.style.height = '1px';
    liveRegion.style.overflow = 'hidden';

    liveRegion.textContent = message;
    document.body.appendChild(liveRegion);

    setTimeout(() => {
      document.body.removeChild(liveRegion);
    }, 1000);
  },

  // Hide from screen readers
  hideFromScreenReaders(element: HTMLElement): void {
    if (typeof window === 'undefined') return;
    element.setAttribute('aria-hidden', 'true');
  },

  // Show to screen readers only
  screenReaderOnly(element: HTMLElement): void {
    if (typeof window === 'undefined') return;
    element.style.position = 'absolute';
    element.style.left = '-10000px';
    element.style.width = '1px';
    element.style.height = '1px';
    element.style.overflow = 'hidden';
  },
};
