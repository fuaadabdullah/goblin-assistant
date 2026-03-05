/**
 * Keyboard Shortcuts Hook
 * Provides global keyboard shortcuts for the application
 */

import { useEffect } from 'react';

interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  callback: () => void;
  description: string;
}

/**
 * Register keyboard shortcuts
 * @param shortcuts - Array of keyboard shortcut configurations
 */
export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const ctrlMatch = shortcut.ctrlKey === undefined || shortcut.ctrlKey === event.ctrlKey;
        const metaMatch = shortcut.metaKey === undefined || shortcut.metaKey === event.metaKey;
        const shiftMatch = shortcut.shiftKey === undefined || shortcut.shiftKey === event.shiftKey;
        const altMatch = shortcut.altKey === undefined || shortcut.altKey === event.altKey;

        if (
          event.key.toLowerCase() === shortcut.key.toLowerCase() &&
          ctrlMatch &&
          metaMatch &&
          shiftMatch &&
          altMatch
        ) {
          event.preventDefault();
          shortcut.callback();
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}

/**
 * Common keyboard shortcuts for the application
 */
export const SHORTCUTS = {
  TOGGLE_HIGH_CONTRAST: {
    key: 'h',
    ctrlKey: true,
    shiftKey: true,
    description: 'Toggle high-contrast mode',
  },
  THEME_NOCTURNE: {
    key: '1',
    ctrlKey: true,
    shiftKey: true,
    description: 'Apply Nocturne theme',
  },
  THEME_EMBER: {
    key: '2',
    ctrlKey: true,
    shiftKey: true,
    description: 'Apply Ember theme',
  },
  THEME_DEFAULT: {
    key: '0',
    ctrlKey: true,
    shiftKey: true,
    description: 'Apply Default theme',
  },
} as const;

/**
 * Format keyboard shortcut for display
 */
export function formatShortcut(shortcut: Partial<KeyboardShortcut>): string {
  const keys: string[] = [];

  if (shortcut.ctrlKey) keys.push('Ctrl');
  if (shortcut.metaKey) keys.push('⌘');
  if (shortcut.shiftKey) keys.push('Shift');
  if (shortcut.altKey) keys.push('Alt');
  if (shortcut.key) keys.push(shortcut.key.toUpperCase());

  return keys.join('+');
}
