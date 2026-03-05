import { Keyboard, Lightbulb } from 'lucide-react';
import { formatShortcut, SHORTCUTS } from '../hooks/useKeyboardShortcuts';

export default function KeyboardShortcutsHelp() {
  const shortcuts = [
    { ...SHORTCUTS.TOGGLE_HIGH_CONTRAST },
    { ...SHORTCUTS.THEME_DEFAULT },
    { ...SHORTCUTS.THEME_NOCTURNE },
    { ...SHORTCUTS.THEME_EMBER },
  ];

  return (
    <div className="bg-surface rounded-xl border border-border p-6">
      <h3 className="text-xl font-semibold text-text mb-4 flex items-center gap-2">
        <Keyboard className="w-6 h-6 text-primary" />
        Keyboard Shortcuts
      </h3>
      <div className="space-y-2">
        {shortcuts.map((shortcut, index) => (
          <div
            key={index}
            className="flex items-center justify-between py-2 border-b border-divider last:border-0"
          >
            <span className="text-muted text-sm">{shortcut.description}</span>
            <kbd className="px-3 py-1 text-xs font-mono bg-bg border border-border rounded text-primary">
              {formatShortcut(shortcut)}
            </kbd>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted mt-4 flex items-center gap-1">
        <Lightbulb className="w-3.5 h-3.5 inline" /> Tip: Use{' '}
        <kbd className="px-1 py-0.5 text-xs font-mono bg-bg border border-border rounded">
          Ctrl+Shift+H
        </kbd>{' '}
        to quickly toggle high-contrast mode
      </p>
    </div>
  );
}
