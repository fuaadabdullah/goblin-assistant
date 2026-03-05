import type { SandboxJob } from '../types';

interface SandboxMainProps {
  /** Current code value. */
  code: string;
  /** Selected language. */
  language: string;
  /** Output logs. */
  logs: string;
  /** Selected job for output display. */
  selectedJob: SandboxJob | null;
  /** Code change handler. */
  onCodeChange: (value: string) => void;
  /** Whether the viewer is in guest mode. */
  isGuest?: boolean;
}

const SandboxMain = ({
  code,
  language,
  logs,
  selectedJob,
  onCodeChange,
  isGuest = false,
}: SandboxMainProps) => (
  <div className="space-y-6">
    <div>
      <h1 className="text-3xl font-bold text-text mb-2">Safe Experiments</h1>
      <p className="text-muted">
        Try automation ideas or code snippets without affecting real data.
      </p>
    </div>

    {isGuest && (
      <div className="bg-surface border border-primary/40 rounded-xl p-4 text-sm text-text">
        <p className="font-semibold text-primary">Guest session</p>
        <p className="text-muted mt-1">
          Runs are temporary and won’t be saved to your history. Sign in to keep results.
        </p>
      </div>
    )}

    <div className="bg-surface rounded-xl shadow-sm border border-border p-6">
      <h2 className="text-lg font-semibold text-text mb-4">Code Editor</h2>
      <textarea
        value={code}
        onChange={e => onCodeChange(e.target.value)}
        placeholder={`Enter your ${language} code here...`}
        className="w-full h-64 px-4 py-3 font-mono text-sm border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent resize-none bg-bg"
      />
      <div className="mt-4 text-xs text-muted">
        <span className="font-medium">Language:</span> {language} |
        <span className="ml-2 font-medium">Lines:</span> {code.split('\n').length}
      </div>
    </div>

    <div className="bg-surface rounded-xl shadow-sm border border-border p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-text">Output & Logs</h2>
        {selectedJob && (
          <span className="text-sm text-muted">
            Job: <span className="font-mono">{selectedJob.id.substring(0, 8)}</span>
          </span>
        )}
      </div>
      <div className="bg-bg text-primary font-mono text-xs p-4 rounded-lg h-64 overflow-y-auto">
        {logs || 'No output yet. Run code to see results.'}
      </div>
    </div>

    {selectedJob && (
      <div className="bg-surface rounded-xl shadow-sm border border-border p-6">
        <h2 className="text-lg font-semibold text-text mb-4">Artifacts</h2>
        <div className="text-sm text-muted">No artifacts generated for this job.</div>
      </div>
    )}
  </div>
);

export default SandboxMain;
