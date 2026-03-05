'use client';

import React from 'react';

export const KeyboardShortcutsHelp: React.FC = () => {
  const shortcuts = [
    {
      key: 'Enter',
      description: 'Send message (when not in text area)',
      category: 'Chat'
    },
    {
      key: 'Shift + Enter',
      description: 'New line in message input',
      category: 'Chat'
    },
    {
      key: 'Ctrl/Cmd + K',
      description: 'Focus search input',
      category: 'Navigation'
    },
    {
      key: 'Ctrl/Cmd + /',
      description: 'Toggle this help panel',
      category: 'UI'
    },
    {
      key: 'Esc',
      description: 'Close active modal/dialog',
      category: 'UI'
    },
    {
      key: 'Ctrl/Cmd + [',
      description: 'Navigate back',
      category: 'Navigation'
    },
    {
      key: 'Ctrl/Cmd + ]',
      description: 'Navigate forward',
      category: 'Navigation'
    },
    {
      key: 'Ctrl/Cmd + P',
      description: 'Open command palette',
      category: 'UI'
    },
  ];

  const groupedShortcuts = shortcuts.reduce((acc, shortcut) => {
    if (!acc[shortcut.category]) {
      acc[shortcut.category] = [];
    }
    acc[shortcut.category].push(shortcut);
    return acc;
  }, {} as Record<string, typeof shortcuts>);

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900 dark:text-white">Keyboard Shortcuts</h3>

      <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
        <div className="text-sm text-gray-600 mb-3">
          Improve your workflow with these keyboard shortcuts
        </div>

        {Object.entries(groupedShortcuts).map(([category, shortcuts]) => (
          <div key={category} className="mb-6">
            <h4 className="font-semibold text-gray-800 mb-3 capitalize">{category}</h4>

            <div className="space-y-2">
              {shortcuts.map((shortcut, index) => (
                <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                  <div className="flex items-center gap-3">
                    <kbd className="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded">
                      {shortcut.key}
                    </kbd>
                    <span className="text-sm text-gray-600">{shortcut.description}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="text-sm text-gray-500">
        Tip: Most shortcuts work globally, but some are context-specific.
      </div>
    </div>
  );
};

export default KeyboardShortcutsHelp;
