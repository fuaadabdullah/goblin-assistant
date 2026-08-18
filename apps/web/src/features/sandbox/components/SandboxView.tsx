import TwoColumnLayout from '../../../components/TwoColumnLayout';
import type { SandboxSessionState } from '../hooks/useSandboxSession';
import type { SandboxJob } from '../types';
import SandboxSidebar from './SandboxSidebar';
import SandboxMain from './SandboxMain';
import Seo from '../../../components/Seo';

interface SandboxViewProps {
  /** Sandbox session state + handlers. */
  session: SandboxSessionState;
  /** Whether the viewer is in guest mode. */
  isGuest?: boolean;
  /** Sandbox availability state. */
  sandboxState?: 'loading' | 'enabled' | 'disabled';
  /** Trigger auth flow when a protected action is attempted. */
  onRequireAuth?: () => void;
}

const SandboxView = ({
  session,
  isGuest = false,
  sandboxState = 'enabled',
  onRequireAuth,
}: SandboxViewProps) => {
  const handleRefresh = () => {
    if (isGuest) {
      onRequireAuth?.();
      return;
    }
    session.refreshJobs();
  };

  const handleSelectJob = (job: SandboxJob) => {
    if (isGuest) {
      onRequireAuth?.();
      return;
    }
    session.selectJob(job);
  };

  const sidebar = (
    <SandboxSidebar
      language={session.language}
      loading={session.loading}
      sandboxState={sandboxState}
      code={session.code}
      jobs={isGuest ? [] : session.jobs}
      jobsError={isGuest ? null : session.jobsError}
      selectedJobId={session.selectedJob?.id}
      onLanguageChange={session.setLanguage}
      onRun={session.runCode}
      onClear={session.clearCode}
      onRefresh={handleRefresh}
      onSelectJob={handleSelectJob}
      isGuest={isGuest}
    />
  );

  const mainContent = (
    <SandboxMain
      code={session.code}
      language={session.language}
      logs={session.logs}
      selectedJob={session.selectedJob}
      sandboxState={sandboxState}
      onCodeChange={session.setCode}
      isGuest={isGuest}
    />
  );

  return (
    <>
      <Seo
        title="Sandbox"
        description="Run safe experiments in Goblin Assistant."
        robots="noindex,nofollow"
      />
      <TwoColumnLayout sidebar={sidebar}>{mainContent}</TwoColumnLayout>
    </>
  );
};

export default SandboxView;
