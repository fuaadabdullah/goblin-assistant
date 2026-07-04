import type { FormEvent } from 'react';
import type { AgentTaskFormState } from '../hooks/useAgentTaskForm';

interface AgentTaskViewProps {
  session: AgentTaskFormState;
}

const statusTone = (status: string) => {
  if (status === 'pr_opened') return 'bg-success/20 text-success border-success/30';
  if (status === 'failed' || status === 'cancelled')
    return 'bg-danger/20 text-danger border-danger/30';
  if (status === 'accepted' || status === 'testing')
    return 'bg-warning/20 text-warning border-warning/30';
  return 'bg-surface text-text-secondary border-border';
};

const phaseLabel = (phase: string) => phase.replace(/_/g, ' ');

const AgentTaskView = ({ session }: AgentTaskViewProps) => {
  const onSubmit = async (event: FormEvent) => {
    await session.submit(event);
  };

  const latestEvents = session.activeTask?.events.slice(-5).reverse() ?? [];

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(255,193,109,0.14),_transparent_30%),linear-gradient(180deg,_#120c06_0%,_#1a1208_40%,_#100b06_100%)] text-text">
      <main className="mx-auto max-w-6xl px-4 py-8 lg:px-8" id="main-content" tabIndex={-1}>
        <section className="mb-8 max-w-3xl">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.35em] text-accent">
            Phase 2 self-development loop
          </p>
          <h1 className="text-4xl font-semibold tracking-tight text-text sm:text-5xl">
            Submit a repo task, watch the worker, review the PR.
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-text-secondary">
            UI requests and GitHub issues normalize into the same task record. The backend keeps
            status, logs, and artifacts; the Fly.io Sprite worker runs Aider, tests, and the PR
            creation flow.
          </p>
        </section>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="overflow-hidden rounded-2xl border border-border/70 bg-surface/90 shadow-card">
            <div className="border-b border-border/70 bg-surface/80 px-6 py-5">
              <h2 className="text-xl font-semibold">Task Intake</h2>
              <p className="mt-1 text-sm text-text-secondary">
                Submit the work item and optional repo/issue context.
              </p>
            </div>
            <div className="space-y-4 px-6 py-6">
              <form className="space-y-4" onSubmit={onSubmit}>
                <p className="rounded-lg border border-border/70 bg-surface/60 px-4 py-3 text-xs leading-5 text-text-secondary">
                  Each submission maps to a persistent Sprite workspace keyed by repo and base
                  branch. The worker restores that workspace, runs Aider with
                  <span className="font-semibold text-text"> router-reason </span>
                  for planning and <span className="font-semibold text-text">router-code</span>
                  for edits, then auto-commits each change batch.
                </p>
                <label className="block space-y-2">
                  <span className="text-sm font-medium text-text">Task</span>
                  <textarea
                    value={session.task}
                    onChange={(e) => session.setTask(e.target.value)}
                    placeholder="Add rate limiting to the chat route and update tests."
                    rows={5}
                    className="w-full rounded-md border border-border bg-surface px-4 py-3 text-sm text-text placeholder:text-text-secondary shadow-sm focus:border-primary focus:outline-none"
                  />
                </label>

                <div className="grid gap-3 md:grid-cols-2">
                  <label className="block space-y-2">
                    <span className="text-sm font-medium text-text">Repo URL</span>
                    <input
                      value={session.repoUrl}
                      onChange={(e) => session.setRepoUrl(e.target.value)}
                      placeholder="https://github.com/acme/goblin-assistant"
                      className="w-full rounded-md border border-border bg-surface px-4 py-3 text-sm text-text placeholder:text-text-secondary shadow-sm focus:border-primary focus:outline-none"
                    />
                  </label>
                  <label className="block space-y-2">
                    <span className="text-sm font-medium text-text">Base branch</span>
                    <input
                      value={session.baseBranch}
                      onChange={(e) => session.setBaseBranch(e.target.value)}
                      placeholder="main"
                      className="w-full rounded-md border border-border bg-surface px-4 py-3 text-sm text-text placeholder:text-text-secondary shadow-sm focus:border-primary focus:outline-none"
                    />
                  </label>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <label className="block space-y-2">
                    <span className="text-sm font-medium text-text">Branch name</span>
                    <input
                      value={session.branchName}
                      onChange={(e) => session.setBranchName(e.target.value)}
                      placeholder="agent/add-rate-limiting"
                      className="w-full rounded-md border border-border bg-surface px-4 py-3 text-sm text-text placeholder:text-text-secondary shadow-sm focus:border-primary focus:outline-none"
                    />
                  </label>
                  <label className="block space-y-2">
                    <span className="text-sm font-medium text-text">Tests command</span>
                    <input
                      value={session.testsCommand}
                      onChange={(e) => session.setTestsCommand(e.target.value)}
                      placeholder="make test-critical"
                      className="w-full rounded-md border border-border bg-surface px-4 py-3 text-sm text-text placeholder:text-text-secondary shadow-sm focus:border-primary focus:outline-none"
                    />
                  </label>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <label className="block space-y-2">
                    <span className="text-sm font-medium text-text">Issue URL</span>
                    <input
                      value={session.issueUrl}
                      onChange={(e) => session.setIssueUrl(e.target.value)}
                      placeholder="https://github.com/acme/goblin-assistant/issues/42"
                      className="w-full rounded-md border border-border bg-surface px-4 py-3 text-sm text-text placeholder:text-text-secondary shadow-sm focus:border-primary focus:outline-none"
                    />
                  </label>
                  <label className="block space-y-2">
                    <span className="text-sm font-medium text-text">Issue number</span>
                    <input
                      value={session.issueNumber}
                      onChange={(e) => session.setIssueNumber(e.target.value)}
                      placeholder="42"
                      inputMode="numeric"
                      className="w-full rounded-md border border-border bg-surface px-4 py-3 text-sm text-text placeholder:text-text-secondary shadow-sm focus:border-primary focus:outline-none"
                    />
                  </label>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <label className="block space-y-2">
                    <span className="text-sm font-medium text-text">Issue title</span>
                    <input
                      value={session.issueTitle}
                      onChange={(e) => session.setIssueTitle(e.target.value)}
                      placeholder="Add rate limiting"
                      className="w-full rounded-md border border-border bg-surface px-4 py-3 text-sm text-text placeholder:text-text-secondary shadow-sm focus:border-primary focus:outline-none"
                    />
                  </label>
                  <label className="block space-y-2">
                    <span className="text-sm font-medium text-text">Issue body</span>
                    <textarea
                      value={session.issueBody}
                      onChange={(e) => session.setIssueBody(e.target.value)}
                      placeholder="Chat route needs request throttling."
                      rows={3}
                      className="w-full rounded-md border border-border bg-surface px-4 py-3 text-sm text-text placeholder:text-text-secondary shadow-sm focus:border-primary focus:outline-none"
                    />
                  </label>
                </div>

                <div className="flex flex-wrap gap-3">
                  <button
                    type="submit"
                    disabled={session.submitting}
                    className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-text-inverse shadow-md transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {session.submitting ? 'Submitting...' : 'Submit task'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      void session.refreshActiveTask();
                    }}
                    disabled={!session.activeTask || session.refreshing}
                    className="inline-flex items-center justify-center rounded-md border border-border bg-surface px-4 py-2 text-sm font-semibold text-text transition hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Refresh status
                  </button>
                  <button
                    type="button"
                    onClick={session.reset}
                    className="inline-flex items-center justify-center rounded-md border border-border bg-surface px-4 py-2 text-sm font-semibold text-text transition hover:bg-surface-hover"
                  >
                    Reset form
                  </button>
                </div>
              </form>

              {session.error && (
                <div className="rounded-md border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
                  {session.error}
                </div>
              )}
            </div>
          </section>

          <section className="overflow-hidden rounded-2xl border border-border/70 bg-surface/90 shadow-card">
            <div className="border-b border-border/70 bg-surface/80 px-6 py-5">
              <h2 className="text-xl font-semibold">Task Status</h2>
              <p className="mt-1 text-sm text-text-secondary">
                Live lifecycle, worker notes, and pull request output.
              </p>
            </div>
            <div className="space-y-5 px-6 py-6">
              {session.activeTask ? (
                <>
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${statusTone(session.activeTask.status)}`}
                    >
                      {session.activeTask.status}
                    </span>
                    <span className="inline-flex rounded-full border border-border bg-surface px-3 py-1 text-xs font-semibold uppercase tracking-wide text-text-secondary">
                      {phaseLabel(session.activeTask.phase)}
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full border border-border bg-surface px-3 py-1 text-xs font-semibold uppercase tracking-wide text-text-secondary">
                      <span aria-hidden="true">↳</span>
                      {session.activeTask.branch_name}
                    </span>
                  </div>

                  <div className="grid gap-3 rounded-xl border border-border bg-surface/70 p-4 text-sm">
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-secondary">Task ID</span>
                      <span className="font-mono text-text">{session.activeTask.task_id}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-secondary">Repo</span>
                      <span className="truncate text-right text-text">{session.activeTask.repo_url}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-secondary">Tests</span>
                      <span className="truncate text-right text-text">{session.activeTask.tests_command}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-secondary">Worker</span>
                      <span className="text-text">
                        {session.activeTask.worker_status || 'pending'}
                        {session.activeTask.worker_error ? ` · ${session.activeTask.worker_error}` : ''}
                      </span>
                    </div>
                    {session.activeTask.pr_url ? (
                      <a
                        href={session.activeTask.pr_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-2 text-primary hover:underline"
                      >
                        Open pull request <span aria-hidden="true">↗</span>
                      </a>
                    ) : null}
                  </div>

                  <div className="grid gap-3 rounded-xl border border-border bg-surface/70 p-4 text-sm">
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-secondary">Workspace</span>
                      <span className="font-mono text-text">
                        {session.activeTask.workspace_id || 'pending'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-secondary">Sprite</span>
                      <span className="font-mono text-text">
                        {session.activeTask.sprite_name || 'pending'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-secondary">Architect model</span>
                      <span className="text-text">
                        {session.activeTask.architect_model || 'router-reason'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-secondary">Editor model</span>
                      <span className="text-text">
                        {session.activeTask.editor_model || 'router-code'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-secondary">Commit policy</span>
                      <span className="text-text">
                        {session.activeTask.auto_commit_each_change ? 'Auto-commit on' : 'Auto-commit off'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-secondary">Repair attempts</span>
                      <span className="text-text">
                        {typeof session.activeTask.repair_attempts === 'number'
                          ? session.activeTask.repair_attempts
                          : '2'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-secondary">Phase 0 CI</span>
                      <span className="text-text">
                        {session.activeTask.phase0_ci_commands?.length
                          ? `${session.activeTask.phase0_ci_commands.length} commands`
                          : 'pytest, lint, build'}
                      </span>
                    </div>
                  </div>

                  <div>
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-text-secondary">
                        Recent events
                      </h3>
                      <span className="text-xs text-text-secondary">
                        {session.refreshing ? 'Refreshing...' : 'Auto-polling'}
                      </span>
                    </div>
                    <div className="space-y-2">
                      {latestEvents.length > 0 ? (
                        latestEvents.map((event) => (
                          <div
                            key={event.event_id}
                            className="rounded-lg border border-border bg-surface/70 px-4 py-3"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <span className="text-sm font-medium text-text">{event.type}</span>
                              <span className="text-xs text-text-secondary">{event.timestamp}</span>
                            </div>
                            <p className="mt-1 text-sm text-text-secondary">{event.message}</p>
                          </div>
                        ))
                      ) : (
                        <div className="rounded-lg border border-dashed border-border bg-surface/60 px-4 py-6 text-sm text-text-secondary">
                          No worker events yet. Once the task dispatches, progress updates will appear
                          here.
                        </div>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <div className="rounded-xl border border-dashed border-border bg-surface/60 px-4 py-8 text-sm text-text-secondary">
                  Submit a task to see the current state, worker acceptance, test results, and PR
                  link.
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

export default AgentTaskView;
