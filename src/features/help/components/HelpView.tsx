import HelpTopics from './HelpTopics';
import HelpSupportForm from './HelpSupportForm';
import type { SupportFormState } from '../hooks/useSupportForm';
import type { StartupDiagnostics } from '../../../utils/startup-diagnostics';
import Seo from '../../../components/Seo';

interface HelpViewProps {
  /** Support form state + handlers. */
  form: SupportFormState;
  /** Optional startup failure context. */
  startupFailure?: {
    logId?: string | null;
    diagnostics?: StartupDiagnostics | null;
    onRetry: () => void;
  };
}

const HelpView = ({ form, startupFailure }: HelpViewProps) => (
  <div className="min-h-screen bg-bg">
    <Seo title="Help" description="Support & documentation for the Goblin AI Gateway." robots="index,follow" />
    <main className="max-w-5xl mx-auto p-6 space-y-6" id="main-content" tabIndex={-1}>
      <header>
        <h1 className="text-3xl font-semibold text-text">Support & Docs</h1>
        <p className="text-sm text-muted">
          Gateway setup, routing policies, cost controls, and incident response.
        </p>
      </header>

      {startupFailure && (
        <section className="rounded-2xl border border-danger/40 bg-danger/5 p-6 space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-text">Startup issue detected</h2>
            <p className="text-sm text-muted">
              Goblin Assistant hit a snag while booting. You can retry or send the
              diagnostics below to support.
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-[1.2fr_1fr]">
            <div className="rounded-xl border border-border bg-bg px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-muted">Diagnostics</p>
              <p className="text-sm text-text mt-2">
                Status: {startupFailure.diagnostics?.status ?? 'unknown'}
              </p>
              <p className="text-sm text-text">
                Message: {startupFailure.diagnostics?.message ?? 'No details captured.'}
              </p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted">
                <div>
                  Auth: {startupFailure.diagnostics?.authMs ?? '—'} ms
                </div>
                <div>
                  Config: {startupFailure.diagnostics?.configMs ?? '—'} ms
                </div>
                <div>
                  Runtime: {startupFailure.diagnostics?.runtimeMs ?? '—'} ms
                </div>
                <div>
                  Total: {startupFailure.diagnostics?.totalMs ?? '—'} ms
                </div>
              </div>
              <p className="text-xs text-muted mt-2">
                Timestamp: {startupFailure.diagnostics?.timestamp ?? 'unknown'}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-bg px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-muted">Log ID</p>
              <p className="text-sm font-mono text-text mt-2">
                {startupFailure.logId ?? startupFailure.diagnostics?.logId ?? 'unknown'}
              </p>
              <button
                onClick={startupFailure.onRetry}
                className="mt-4 w-full rounded-lg bg-primary text-text-inverse px-4 py-2 text-sm font-medium hover:brightness-110"
                type="button"
              >
                Retry boot
              </button>
            </div>
          </div>
        </section>
      )}

      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <HelpTopics
          topics={[
            {
              title: 'Getting started',
              body: 'Learn how to ask questions and organize your chats.',
            },
            {
              title: 'Search tips',
              body: 'Use keywords, names, and dates to sharpen results.',
            },
            {
              title: 'Safe experiments',
              body: 'Try automation or code snippets without risk.',
            },
          ]}
        />

        <HelpSupportForm
          message={form.message}
          sent={form.sent}
          error={form.error}
          sending={form.sending}
          onMessageChange={form.setMessage}
          onSubmit={form.handleSubmit}
        />
      </div>
    </main>
  </div>
);

export default HelpView;
