
'use client';

// Motion preference utilities
export const motion = {
  // Check if user prefers reduced motion
  prefersReducedMotion(): boolean {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  },

  // Create motion-safe animation
  createMotionSafeAnimation(callback: () => void): void {
    if (!this.prefersReducedMotion()) {
      callback();
    }
  },

  // Get motion-safe transition
  getMotionSafeTransition(property: string = 'all', duration: string = '300ms'): string {
    return this.prefersReducedMotion() ? 'none' : `${property} ${duration} ease-in-out`;
  },
};
