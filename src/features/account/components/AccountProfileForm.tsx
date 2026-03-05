import type { FormEvent } from 'react';

interface AccountProfileFormProps {
  /** Name field value. */
  name: string;
  /** Email value (read-only). */
  email: string;
  /** Whether a save confirmation is visible. */
  saved: boolean;
  /** Optional error message to display. */
  error?: string | null;
  /** Whether the form is currently saving. */
  saving?: boolean;
  /** Change handler for name. */
  onNameChange: (value: string) => void;
  /** Save handler. */
  onSave: (e: FormEvent) => void;
}

const AccountProfileForm = ({
  name,
  email,
  saved,
  error,
  saving,
  onNameChange,
  onSave,
}: AccountProfileFormProps) => (
  <form onSubmit={onSave} className="bg-surface border border-border rounded-2xl p-6 space-y-4">
    <h2 className="text-lg font-semibold text-text">Profile</h2>
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <label className="block text-sm font-medium text-text mb-2" htmlFor="account-name">
          Full name
        </label>
        <input
          id="account-name"
          value={name}
          onChange={e => onNameChange(e.target.value)}
          placeholder="Your name"
          className="w-full px-4 py-3 border border-border rounded-lg bg-surface-hover text-text"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-text mb-2" htmlFor="account-email">
          Email
        </label>
        <input
          id="account-email"
          value={email}
          disabled
          className="w-full px-4 py-3 border border-border rounded-lg bg-surface-hover text-text opacity-80"
        />
      </div>
    </div>
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="submit"
        disabled={saving}
        className="px-4 py-2 rounded-lg bg-primary text-text-inverse font-medium shadow-glow-primary hover:brightness-110 disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {saving ? 'Saving...' : 'Save Changes'}
      </button>
      {saved && <span className="text-sm text-success">Saved.</span>}
      {error && <span className="text-sm text-danger">{error}</span>}
    </div>
  </form>
);

export default AccountProfileForm;
