import { Contrast, Moon, Sun } from 'lucide-react';
import { useContrastMode } from '../hooks/useContrastMode';

const MODE_LABELS = {
  dark: 'Dark',
  light: 'Light',
  high: 'High Contrast',
} as const;

const MODE_ICONS = {
  dark: Moon,
  light: Sun,
  high: Contrast,
} as const;

export default function ContrastModeToggle() {
  const { mode, toggleMode } = useContrastMode();
  const Icon = MODE_ICONS[mode];

  return (
    <button
      onClick={toggleMode}
      className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface hover:bg-surface-hover border border-border transition-colors"
      aria-label={`Current theme: ${MODE_LABELS[mode]}. Click to switch.`}
      title={`Theme: ${MODE_LABELS[mode]}`}
    >
      <Icon className="w-5 h-5" aria-hidden="true" />
      <span className="text-sm font-medium">{MODE_LABELS[mode]}</span>
    </button>
  );
}
