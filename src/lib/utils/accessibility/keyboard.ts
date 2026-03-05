
'use client';

// Keyboard navigation utilities
export const keyboard = {
  // Common key codes
  keys: {
    ENTER: 13,
    ESCAPE: 27,
    SPACE: 32,
    TAB: 9,
    ARROW_UP: 38,
    ARROW_DOWN: 40,
    ARROW_LEFT: 37,
    ARROW_RIGHT: 39,
    HOME: 36,
    END: 35,
  },

  // Is navigation key
  isNavigationKey(keyCode: number): boolean {
    return [
      this.keys.TAB,
      this.keys.ARROW_UP,
      this.keys.ARROW_DOWN,
      this.keys.ARROW_LEFT,
      this.keys.ARROW_RIGHT,
      this.keys.HOME,
      this.keys.END,
    ].includes(keyCode);
  },

  // Create keyboard handler
  createHandler(handlers: Record<string, (e: KeyboardEvent) => void>): (e: KeyboardEvent) => void {
    return (e: KeyboardEvent) => {
      const handler = handlers[e.key];
      if (handler) {
        handler(e);
        e.preventDefault();
        e.stopPropagation();
      }
    };
  },
};
