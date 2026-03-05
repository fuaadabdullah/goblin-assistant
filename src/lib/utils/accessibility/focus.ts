
'use client';

// Focus management
export const focusManager = {
  // Store focus
  storeFocus(): void {
    if (typeof window === 'undefined') return;
    const activeElement = document.activeElement as HTMLElement;
    sessionStorage.setItem('lastFocus', activeElement?.id || '');
  },

  // Restore focus
  restoreFocus(): void {
    if (typeof window === 'undefined') return;
    const lastFocusId = sessionStorage.getItem('lastFocus');
    if (lastFocusId) {
      const element = document.getElementById(lastFocusId);
      if (element) {
        element.focus();
      }
    }
  },

  // Focus trap - fixes NodeListOf issue
  createFocusTrap(container: HTMLElement): () => void {
    if (typeof window === 'undefined') return () => {};

    const focusableElements = Array.from(
      container.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
    ) as HTMLElement[];

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleKeyDown = (e: KeyboardEvent): void => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    container.addEventListener('keydown', handleKeyDown);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  },

  // Focus visible polyfill
  initFocusVisible(): void {
    if (typeof window === 'undefined') return;
    document.addEventListener('keydown', () => {
      document.body.classList.add('js-focus-visible');
    });

    document.addEventListener('mousedown', () => {
      document.body.classList.remove('js-focus-visible');
    });
  },
};
