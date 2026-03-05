import type { FormEvent } from 'react';
import Link from 'next/link';

interface HelpSupportFormProps {
  /** Current message value. */
  message: string;
  /** Whether submission confirmation is visible. */
  sent: boolean;
  /** Optional error message. */
  error?: string | null;
  /** Whether the form is currently sending. */
  sending?: boolean;
  /** Message change handler. */
  onMessageChange: (value: string) => void;
  /** Submit handler. */
  onSubmit: (e: FormEvent) => void;
}

const HelpSupportForm = ({
  message,
  sent,
  error,
  sending,
  onMessageChange,
  onSubmit,
}: HelpSupportFormProps) => (
  <section className="bg-surface border border-border rounded-2xl p-6 space-y-4">
    <h2 className="text-lg font-semibold text-text">Chat with Support</h2>
    <p className="text-sm text-muted">
      Describe the issue and we will connect you with a human.
    </p>
    <form onSubmit={onSubmit} className="space-y-3">
      <textarea
        value={message}
        onChange={e => onMessageChange(e.target.value)}
        placeholder="Tell us what you need help with..."
        rows={4}
        className="w-full px-3 py-2 rounded-lg border border-border bg-surface-hover text-sm text-text"
      />
      <button
        type="submit"
        disabled={sending}
        className="w-full px-4 py-2 rounded-lg bg-primary text-text-inverse font-medium shadow-glow-primary hover:brightness-110 disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {sending ? 'Sending...' : 'Send to Support'}
      </button>
      {sent && <p className="text-xs text-success">Message sent.</p>}
      {error && <p className="text-xs text-danger">{error}</p>}
    </form>
    <div className="text-xs text-muted">
      Prefer to self-serve?{' '}
      <Link href="/chat" className="text-primary hover:underline">
        Start a guided chat
      </Link>
      .
    </div>
  </section>
);

export default HelpSupportForm;
