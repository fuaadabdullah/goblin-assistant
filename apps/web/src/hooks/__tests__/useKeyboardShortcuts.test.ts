import { act, renderHook } from '@testing-library/react';
import { useKeyboardShortcuts, formatShortcut, SHORTCUTS } from '../useKeyboardShortcuts';

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
    const callback = vi.fn();
    const shortcuts = [
      {
        key: 'Enter',
        ctrlKey: true,
        callback,
        description: 'Submit',
      },
    ];

    const { unmount } = renderHook(() => useKeyboardShortcuts(shortcuts));

    const event = new KeyboardEvent('keydown', {
      key: 'Enter',
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });

    act(() => {
      window.dispatchEvent(event);
    });

    expect(callback).toHaveBeenCalledTimes(1);
    expect(event.defaultPrevented).toBe(true);

    unmount();

    act(() => {
      window.dispatchEvent(
        new KeyboardEvent('keydown', {
          key: 'Enter',
          ctrlKey: true,
          bubbles: true,
          cancelable: true,
        })
      );
    });

    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should handle multiple shortcuts', () => {
    const callbacks = {
      save: vi.fn(),
      search: vi.fn(),
      help: vi.fn(),
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
