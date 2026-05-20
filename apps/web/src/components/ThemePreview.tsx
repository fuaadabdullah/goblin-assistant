import { useEffect, useState } from 'react';
import { applyThemePreset } from '../theme/theme';

const THEME_STORAGE_KEY = 'goblinos-theme-preference'; // Align with core theme system

// Theme preset metadata for UI display
const THEME_PRESETS = [
  {
    id: 'default',
    name: 'Goblin Default',
    description: 'Original neon green + magenta stack',
    colors: { primary: '#06D06A', accent: '#FF2AA8', cta: '#FF6A1A' },
  },
  {
    id: 'nocturne',
    name: 'Nocturne Violet',
    description: 'Deep indigo surfaces with electric cyan accents',
    colors: { primary: '#51F8E3', accent: '#C964FF', cta: '#FF8C32' },
  },
  {
    id: 'ember',
    name: 'Ember Blaze',
    description: 'Warm amber primary with teal highlights',
    colors: { primary: '#17E0C1', accent: '#FF4DA6', cta: '#FFB347' },
  },
] as const;

type ThemeId = (typeof THEME_PRESETS)[number]['id'];

export default function ThemePreview() {
  const [activeTheme, setActiveTheme] = useState<ThemeId>(() => {
    if (typeof window === 'undefined') {
      return 'default';
    }
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY) as ThemeId | null;
    return stored ?? 'default';
  });

  useEffect(() => {
    // Use core theme system's applyThemePreset
    applyThemePreset(activeTheme);
  }, [activeTheme]);

  return (
    <section className="bg-surface rounded-xl border border-border p-6 space-y-6">
      <header className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Theme Preview</p>
          <h3 className="text-2xl font-semibold text-text">Swap palettes instantly</h3>
          <p className="text-sm text-muted">Palettes update CSS vars + glow tokens in real time.</p>
        </div>
        <div className="flex gap-2">
          {THEME_PRESETS.map(preset => (
            <button
              key={preset.id}
              onClick={() => setActiveTheme(preset.id)}
              className={`px-3 py-1 rounded-full text-xs font-semibold border transition
                ${
                  activeTheme === preset.id
                    ? 'border-primary text-primary bg-primary/10'
                    : 'border-border text-muted hover:text-primary'
                }
              `}
            >
              {preset.name}
            </button>
          ))}
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        {THEME_PRESETS.map(preset => (
          <div
            key={preset.id}
            className={`rounded-lg border p-4 transition bg-surface
              ${activeTheme === preset.id ? 'border-primary shadow-glow-primary' : 'border-border'}
            `}
          >
            <p className="text-sm font-semibold text-text">{preset.name}</p>
            <p className="text-xs text-muted mb-3">{preset.description}</p>
            <div className="flex gap-2">
              <div
                className="h-10 w-10 rounded-full border border-border"
                style={{ backgroundColor: preset.colors.primary }}
                title={`Primary: ${preset.colors.primary}`}
              />
              <div
                className="h-10 w-10 rounded-full border border-border"
                style={{ backgroundColor: preset.colors.accent }}
                title={`Accent: ${preset.colors.accent}`}
              />
              <div
                className="h-10 w-10 rounded-full border border-border"
                style={{ backgroundColor: preset.colors.cta }}
                title={`CTA: ${preset.colors.cta}`}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
