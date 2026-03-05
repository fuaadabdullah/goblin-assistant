import { useContrastMode } from '../hooks/useContrastMode';

export default function ContrastModeToggle() {
  const { mode, toggleMode } = useContrastMode();

  return (
    <button
      onClick={toggleMode}
      className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface hover:bg-surface-hover border border-border transition-colors"
      aria-label={`Switch to ${mode === 'standard' ? 'high' : 'standard'} contrast mode`}
      title={`Current: ${mode === 'standard' ? 'Standard' : 'High'} Contrast`}
    >
      <svg
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        {mode === 'standard' ? (
          // Eye icon for standard mode (switching to high contrast)
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
          />
        ) : (
          // Contrast icon for high contrast mode (switching to standard)
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
          />
        )}
      </svg>
      <span className="text-sm font-medium">
        {mode === 'standard' ? 'Standard' : 'High'} Contrast
      </span>
    </button>
  );
}
