import { Play, Trash2, RefreshCw, Zap } from 'lucide-react';
import type { SandboxJob } from '../types';

interface SandboxSidebarProps {
  /** Current language selection. */
  language: string;
  /** Whether a run is in progress. */
  loading: boolean;
  /** Current code value (for enabling run). */
  code: string;
  /** Jobs list. */
  jobs: SandboxJob[];
  /** Selected job id. */
  selectedJobId?: string;
  /** Language change handler. */
  onLanguageChange: (value: string) => void;
  /** Run handler. */
  onRun: () => void;
  /** Clear code handler. */
  onClear: () => void;
  /** Refresh jobs handler. */
  onRefresh: () => void;
  /** Job selection handler. */
  onSelectJob: (job: SandboxJob) => void;
  /** Whether viewer is in guest mode. */
  isGuest?: boolean;
}

const SandboxSidebar = ({
  language,
  loading,
  code,
  jobs,
  selectedJobId,
  onLanguageChange,
  onRun,
  onClear,
  onRefresh,
  onSelectJob,
  isGuest = false,
}: SandboxSidebarProps) => (
  <div className="space-y-4">
    <div>
      <h2 className="text-lg font-semibold text-text mb-3">Sandbox</h2>
      <p className="text-xs text-muted mb-4">
        Try experimental features and run automation safely.
      </p>
    </div>

    <div>
      <label htmlFor="sandbox-language" className="block text-xs font-medium text-text mb-2">Language</label>
      <select
        id="sandbox-language"
        value={language}
        onChange={e => onLanguageChange(e.target.value)}
        className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-surface-hover focus:ring-2 focus:ring-primary"
      >
        <option value="python">Python</option>
      </select>
      <p className="mt-2 text-xs text-muted">
        GCP sandbox execution currently supports Python.
      </p>
    </div>

    <div className="space-y-2">
      <button
        onClick={onRun}
        disabled={!code || loading}
        className="w-full px-3 py-2 text-sm font-medium text-text-inverse bg-success rounded-lg hover:bg-success/90 disabled:bg-surface-hover disabled:cursor-not-allowed transition-colors shadow-glow-primary"
      >
        {loading ? <><Zap className="w-4 h-4 inline mr-1" />Running...</> : <><Play className="w-4 h-4 inline mr-1" />Run Code</>}
      </button>
      <button
        onClick={onClear}
        className="w-full px-3 py-2 text-sm font-medium text-text bg-surface-hover rounded-lg hover:bg-surface-active transition-colors"
      >
        <Trash2 className="w-4 h-4 inline mr-1" />Clear
      </button>
      <button
        onClick={onRefresh}
        className="w-full px-3 py-2 text-sm font-medium text-primary bg-primary/20 rounded-lg hover:bg-primary/30 transition-colors"
      >
        <RefreshCw className="w-4 h-4 inline mr-1" />Refresh Jobs
      </button>
    </div>

    <div className="space-y-2">
      <h3 className="text-xs font-semibold text-text uppercase tracking-wide">Recent Jobs</h3>
      {isGuest ? (
        <div className="text-xs text-muted">
          Sign in to view your saved runs and logs.
        </div>
      ) : jobs.length > 0 ? (
        jobs.slice(0, 10).map(job => (
          <button
            key={job.id}
            onClick={() => onSelectJob(job)}
            className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${selectedJobId === job.id
              ? 'bg-primary/20 text-primary border border-primary'
              : 'bg-surface border border-border text-text hover:bg-surface-hover'
              }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono">{job.id.substring(0, 8)}</span>
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${job.status === 'completed'
                  ? 'bg-success/20 text-success'
                  : job.status === 'failed'
                    ? 'bg-danger/20 text-danger'
                    : job.status === 'running'
                      ? 'bg-info/20 text-info'
                      : 'bg-surface-hover text-muted'
                  }`}
              >
                {job.status}
              </span>
            </div>
            <div className="text-xs text-muted">{new Date(job.created_at).toLocaleString()}</div>
          </button>
        ))
      ) : (
        <div className="text-xs text-muted">No jobs yet</div>
      )}
    </div>
  </div>
);

export default SandboxSidebar;
