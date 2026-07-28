import type { FormEvent } from 'react';
import type { TriageResponse } from '../api';
import { Button, InlineErrorState } from '../../../components/ui';

const PRIORITY_BADGE: Record<string, string> = {
  P0: 'bg-red-100 text-red-800',
  P1: 'bg-orange-100 text-orange-800',
  P2: 'bg-yellow-100 text-yellow-800',
  P3: 'bg-green-100 text-green-800',
};

interface BugReportFormProps {
  description: string;
  submitting: boolean;
  result: TriageResponse | null;
  error: string | null;
  onDescriptionChange: (value: string) => void;
  onSubmit: (e: FormEvent) => void;
  onReset: () => void;
}

const BugReportForm = ({
  description,
  submitting,
  result,
  error,
  onDescriptionChange,
  onSubmit,
  onReset,
}: BugReportFormProps) => (
  <section className="bg-surface border border-border rounded-2xl p-6 space-y-4">
    <h2 className="text-lg font-semibold text-text">Report a Bug</h2>
    <p className="text-sm text-muted">
      Even &ldquo;it broke&rdquo; works. AI will figure out the rest.
    </p>

    {result ? (
      <div className="space-y-4">
        <div className="rounded-xl border border-border bg-surface-hover p-4 space-y-3">
          <p className="text-sm font-medium text-text">{result.triage.title}</p>
          <div className="flex flex-wrap gap-2 text-xs">
            <span
              className={`rounded-full px-2 py-0.5 font-medium ${PRIORITY_BADGE[result.triage.priority] ?? 'bg-muted/20 text-muted'}`}
            >
              {result.triage.priority}
            </span>
            <span className="rounded-full bg-muted/10 px-2 py-0.5 text-muted">
              {result.triage.category}
            </span>
            <span className="rounded-full bg-muted/10 px-2 py-0.5 text-muted">
              {result.triage.affected_service}
            </span>
          </div>
          <p className="text-xs text-muted">{result.triage.cleaned_description}</p>
          {result.issue_url && (
            <a
              href={result.issue_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
            >
              GitHub issue #{result.issue_number} &rarr;
            </a>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={onReset} type="button">
          Report another
        </Button>
      </div>
    ) : (
      <form onSubmit={onSubmit} className="space-y-3">
        <textarea
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="Describe the problem — even 'it broke' is fine"
          rows={4}
          className="w-full px-3 py-2 rounded-lg border border-border bg-surface-hover text-sm text-text"
        />
        <Button type="submit" disabled={submitting} fullWidth loading={submitting}>
          {submitting ? 'Triaging...' : 'Triage & Create Issue'}
        </Button>
        {error && <InlineErrorState title="Triage failed" message={error} />}
      </form>
    )}
  </section>
);

export default BugReportForm;
