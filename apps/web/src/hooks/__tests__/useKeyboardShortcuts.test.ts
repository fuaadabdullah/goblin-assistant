import { renderHook } from '@testing-library/react';
import {
  useKeyboardShortcuts,
  formatShortcut,
  SHORTCUTS,
} from '../useKeyboardShortcuts';

describe('useKeyboardShortcuts', () => {
  it('should format keyboard shortcuts correctly', () => {
    expect(formatShortcut({ ctrlKey: true, key: 's' })).toContain('Ctrl');
    expect(formatShortcut({ metaKey: true, key: 'k' })).toContain('⌘');
    expect(formatShortcut({ shiftKey: true, key: 'a' })).toContain('Shift');
  });

  it('should return predefined shortcuts', () => {
    expect(SHORTCUTS).toBeDefined();
    expect(SHORTCUTS.TOGGLE_HIGH_CONTRAST).toBeDefined();
    expect(SHORTCUTS.THEME_NOCTURNE).toBeDefined();
    expect(SHORTCUTS.THEME_EMBER).toBeDefined();
    expect(SHORTCUTS.THEME_DEFAULT).toBeDefined();
  });

  it('should register keyboard shortcuts', () => {
    const callback = jest.fn();
    const shortcuts = [
      {
        key: 'Enter',
        ctrlKey: true,
        callback,
        description: 'Submit',
      },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));
    // Hook should register without errors
  });

  it('should handle multiple shortcuts', () => {
    const callbacks = {
      save: jest.fn(),
      search: jest.fn(),
      help: jest.fn(),
    };

    const shortcuts = [
      { key: 's', ctrlKey: true, callback: callbacks.save, description: 'Save' },
      { key: 'k', ctrlKey: true, callback: callbacks.search, description: 'Search' },
      { key: '?', shiftKey: true, callback: callbacks.help, description: 'Help' },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));
  });

  it('should format combined modifiers', () => {
    const formatted = formatShortcut({
      key: 'a',
      ctrlKey: true,
      shiftKey: true,
      altKey: true,
    });

    expect(formatted).toContain('Ctrl');
    expect(formatted).toContain('Shift');
    expect(formatted).toContain('Alt');
    expect(formatted).toContain('A');
  });
});
