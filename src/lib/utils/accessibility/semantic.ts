
'use client';

// Semantic HTML utilities
export const semantic = {
  // Create semantic heading
  createHeading(level: 1 | 2 | 3 | 4 | 5 | 6, text: string, className?: string): HTMLElement {
    if (typeof window === 'undefined') throw new Error('Cannot create DOM elements on server side');

    const heading = document.createElement(`h${level}`);
    heading.textContent = text;
    if (className) {
      heading.className = className;
    }
    return heading;
  },

  // Validate heading hierarchy
  validateHeadingHierarchy(container: HTMLElement): boolean {
    if (typeof window === 'undefined') return false;

    const headings = Array.from(container.querySelectorAll('h1, h2, h3, h4, h5, h6'));
    let lastLevel = 0;

    for (const heading of headings) {
      const level = parseInt(heading.tagName.charAt(1), 10);

      if (level > lastLevel + 1) {
        console.warn(
          `Invalid heading hierarchy: ${heading.tagName} follows a heading of level ${lastLevel}`
        );
        return false;
      }

      lastLevel = level;
    }

    return true;
  },
};
