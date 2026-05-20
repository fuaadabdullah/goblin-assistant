import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('lucide-react', () =>
  new Proxy({}, {
    get: (_, name) => {
      if (name === '__esModule') return true;
      return (props: Record<string, unknown>) => <span data-testid={`icon-${String(name)}`} {...props} />;
    },
  })
);

jest.mock('@/hooks/useKeyboardShortcuts', () => ({
  formatShortcut: (s: { key: string; ctrlKey?: boolean; shiftKey?: boolean }) => {
    const parts: string[] = [];
    if (s.ctrlKey) parts.push('Ctrl');
    if (s.shiftKey) parts.push('Shift');
    parts.push(s.key.toUpperCase());
    return parts.join('+');
  },
  SHORTCUTS: {
    TOGGLE_HIGH_CONTRAST: { key: 'h', ctrlKey: true, shiftKey: true, description: 'Toggle High Contrast' },
    THEME_DEFAULT: { key: '1', ctrlKey: true, shiftKey: true, description: 'Goblin Default' },
    THEME_NOCTURNE: { key: '2', ctrlKey: true, shiftKey: true, description: 'Nocturne' },
    THEME_EMBER: { key: '3', ctrlKey: true, shiftKey: true, description: 'Ember' },
  },
}));

import KeyboardShortcutsHelp from '../KeyboardShortcutsHelp';

describe('KeyboardShortcutsHelp', () => {
  it('renders the heading', () => {
    render(<KeyboardShortcutsHelp />);
    expect(screen.getByText('Keyboard Shortcuts')).toBeInTheDocument();
  });

  it('shows all four shortcut descriptions', () => {
    render(<KeyboardShortcutsHelp />);
    expect(screen.getByText('Toggle High Contrast')).toBeInTheDocument();
    expect(screen.getByText('Goblin Default')).toBeInTheDocument();
    expect(screen.getByText('Nocturne')).toBeInTheDocument();
    expect(screen.getByText('Ember')).toBeInTheDocument();
  });

  it('renders formatted shortcuts', () => {
    render(<KeyboardShortcutsHelp />);
    // Ctrl+Shift+H appears twice: once in the shortcuts list and once in the tip
    expect(screen.getAllByText('Ctrl+Shift+H').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Ctrl+Shift+1')).toBeInTheDocument();
    expect(screen.getByText('Ctrl+Shift+2')).toBeInTheDocument();
    expect(screen.getByText('Ctrl+Shift+3')).toBeInTheDocument();
  });

  it('shows the tip text', () => {
    render(<KeyboardShortcutsHelp />);
    expect(screen.getByText(/Tip: Use/)).toBeInTheDocument();
  });

  it('renders Keyboard and Lightbulb icons', () => {
    render(<KeyboardShortcutsHelp />);
    expect(screen.getByTestId('icon-Keyboard')).toBeInTheDocument();
    expect(screen.getByTestId('icon-Lightbulb')).toBeInTheDocument();
  });
});
