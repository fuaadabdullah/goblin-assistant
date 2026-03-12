'use client';

type Mode = 'all' | 'finance' | 'learn' | 'general';

interface ModeSelectorProps {
  activeMode: Mode;
  onModeChange: (mode: Mode) => void;
}

const MODES: { key: Mode; label: string }[] = [
  { key: 'all', label: '✨ All' },
  { key: 'finance', label: '📈 Finance' },
  { key: 'learn', label: '🎓 Learn' },
  { key: 'general', label: '⚡ General' },
];

const ModeSelector = ({ activeMode, onModeChange }: ModeSelectorProps) => (
  <div className="flex gap-2 flex-wrap justify-center" aria-label="Chat mode">
    {MODES.map(({ key, label }) => (
      <button
        key={key}
        onClick={() => onModeChange(key)}
        type="button"
        className={[
          'px-4 py-1.5 rounded-full text-sm font-medium transition-colors duration-150',
          activeMode === key
            ? 'bg-primary text-white shadow-sm'
            : 'bg-surface border border-border text-muted hover:text-text hover:border-primary/50',
        ].join(' ')}
      >
        {label}
      </button>
    ))}
  </div>
);

export default ModeSelector;
