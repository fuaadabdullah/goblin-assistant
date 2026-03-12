import { useContrastMode } from '../hooks/useContrastMode';

const MODE_LABELS = {
  dark: 'Dark',
  light: 'Light',
  high: 'High Contrast',
} as const;

export default function ContrastModeToggle() {
  const { mode, toggleMode } = useContrastMode();

  return (
    <button
      onClick={toggleMode}
      className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface hover:bg-surface-hover border border-border transition-colors"
      aria-label={`Current theme: ${MODE_LABELS[mode]}. Click to switch.`}
      title={`Theme: ${MODE_LABELS[mode]}`}
    >
      <svg
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        {mode === 'dark' && (
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
          />
        )}
        {mode === 'light' && (
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
          />
        )}
        {mode === 'high' && (
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
          />
        )}
      </svg>
      <span className="text-sm font-medium">
        {MODE_LABELS[mode]}
      </span>
    </button>
  );
}
