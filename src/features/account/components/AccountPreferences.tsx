import type { AccountPreferencesPayload } from '../types';

interface AccountPreferencesProps {
  /** Current preference values. */
  preferences: AccountPreferencesPayload;
  /** Toggle handler. */
  onToggle: (key: keyof AccountPreferencesPayload) => void;
}

const AccountPreferences = ({ preferences, onToggle }: AccountPreferencesProps) => (
  <section className="bg-surface border border-border rounded-2xl p-6 space-y-4">
    <h2 className="text-lg font-semibold text-text">Preferences</h2>
    {[
      {
        key: 'summaries',
        label: 'Auto-summarize long answers',
        description: 'Keeps replies short and easy to scan.',
      },
      {
        key: 'notifications',
        label: 'Email me important updates',
        description: 'Only critical changes or alerts.',
      },
      {
        key: 'familyMode',
        label: 'Plain-language mode',
        description: 'Less jargon. More direct steps.',
      },
    ].map(item => (
      <label
        key={item.key}
        className="flex items-start justify-between gap-4 border border-border rounded-xl p-4 bg-surface-hover"
      >
        <span>
          <span className="block text-sm font-medium text-text">{item.label}</span>
          <span className="block text-xs text-muted">{item.description}</span>
        </span>
        <input
          type="checkbox"
          checked={preferences[item.key as keyof AccountPreferencesPayload]}
          onChange={() => onToggle(item.key as keyof AccountPreferencesPayload)}
          className="h-5 w-5 accent-primary"
        />
      </label>
    ))}
  </section>
);

export default AccountPreferences;
