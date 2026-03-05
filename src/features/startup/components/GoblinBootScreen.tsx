import StatusLine from './StatusLine';
import GoblinLoader from './GoblinLoader';
import type { StartupStatus } from '../types';

interface GoblinBootScreenProps {
  status: StartupStatus;
  message: string;
}

const steps: Array<{ id: StartupStatus; label: string }> = [
  { id: 'checking-auth', label: 'Checking authentication' },
  { id: 'loading-config', label: 'Loading configuration' },
  { id: 'initializing-runtime', label: 'Initializing runtime' },
  { id: 'ready', label: 'Ready to launch' },
];

const GoblinBootScreen = ({ status, message }: GoblinBootScreenProps) => {
  const currentIndex = steps.findIndex(step => step.id === status);

  return (
    <div className="min-h-screen bg-bg text-text flex items-center justify-center px-6">
      <div className="w-full max-w-2xl">
        <div className="rounded-3xl border border-border bg-surface/80 backdrop-blur shadow-xl p-8 md:p-10">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-muted">Goblin Assistant</p>
              <h1 className="text-3xl md:text-4xl font-semibold mt-3">
                Initializing gateway
              </h1>
              <p className="text-sm text-muted mt-2">
                Connecting to provider networks. Syncing routing policies and cost limits.
              </p>
            </div>
            <GoblinLoader size={64} />
          </div>

          <div className="mt-8 grid gap-3">
            {steps.map((step, index) => {
              const state: 'complete' | 'active' | 'pending' | 'error' =
                status === 'error'
                  ? 'error'
                  : index < currentIndex
                    ? 'complete'
                    : index === currentIndex
                      ? 'active'
                      : 'pending';
              return <StatusLine key={step.id} label={step.label} state={state} />;
            })}
          </div>

          <div className="mt-8 rounded-2xl bg-bg border border-border px-4 py-3">
            <p className="text-sm text-muted">Status update</p>
            <p className="text-base font-medium text-text mt-1">{message}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GoblinBootScreen;
