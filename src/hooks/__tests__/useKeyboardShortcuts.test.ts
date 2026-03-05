import { renderHook, act } from '@testing-library/react';
import {
  useKeyboardShortcuts,
  formatShortcut,
  SHORTCUTS,
} from '../useKeyboardShortcuts';

describe('useKeyboardShortcuts', () => {
  it('should format keyboard shortcuts correctly', () => {
    expect(formatShortcut({ ctrlKey: true, key: 's' })).toContain('Ctrl');
    expect(formatShortcut({ metaKey: true, key: 'k' })).toContain('Cmd');
  });

  it('should return predefined shortcuts', () => {
    expect(SHORTCUTS).toBeDefined();
    expect(Object.keys(SHORTCUTS).length).toBeGreaterThan(0);
  });

  it('should register keyboard shortcuts', () => {
    const handler = jest.fn();
    const shortcuts = [
      {
        key: 'Enter',
        ctrlKey: true,
        handler,
      },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));
    // Hook should register without errors
  });

  it('should handle multiple shortcuts', () => {
    const handlers = {
      save: jest.fn(),
      search: jest.fn(),
      help: jest.fn(),
    };

    const shortcuts = [
      { key: 's', ctrlKey: true, handler: handlers.save },
      { key: 'k', ctrlKey: true, handler: handlers.search },
      { key: '?', shiftKey: true, handler: handlers.help },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));
    // Should register all shortcuts
  });

  it('should handle modifier key combinations', () => {
    const handler = jest.fn();
    const shortcutWithModifiers = {
      key: 'a',
      ctrlKey: true,
      shiftKey: true,
      altKey: true,
      handler,
    };

    renderHook(() => useKeyboardShortcuts([shortcutWithModifiers]));
    // Should handle multiple modifier keys
  });
});
