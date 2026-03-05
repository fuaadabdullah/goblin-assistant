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
  /** Trigger auth flow when a protected action is attempted. */
  onRequireAuth?: () => void;
}

const SandboxView = ({ session, isGuest = false, onRequireAuth }: SandboxViewProps) => {
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
      code={session.code}
      jobs={isGuest ? [] : session.jobs}
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
      onCodeChange={session.setCode}
      isGuest={isGuest}
    />
  );

  return (
    <>
      <Seo title="Sandbox" description="Run safe experiments in Goblin Assistant." robots="noindex,nofollow" />
      <TwoColumnLayout sidebar={sidebar}>{mainContent}</TwoColumnLayout>
    </>
  );
};

export default SandboxView;
