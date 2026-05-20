import type { FC } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import { useSupportForm } from './hooks/useSupportForm';
import HelpView from './components/HelpView';
import type { StartupDiagnostics } from '../../utils/startup-diagnostics';
import { readStartupDiagnostics, clearStartupDiagnostics } from '../../utils/startup-diagnostics';

const HelpScreen: FC = () => {
  const form = useSupportForm();
  const router = useRouter();
  const [startupDiagnostics, setStartupDiagnostics] = useState<StartupDiagnostics | null>(null);

  const isStartupFailed = useMemo(() => {
    if (!router.isReady) return false;
    const reason = router.query.reason;
    return reason === 'startup_failed' || (Array.isArray(reason) && reason.includes('startup_failed'));
  }, [router.isReady, router.query.reason]);

  useEffect(() => {
    if (!isStartupFailed) return;
    setStartupDiagnostics(readStartupDiagnostics());
  }, [isStartupFailed]);

  const logId = useMemo(() => {
    if (!router.isReady) return null;
    const value = router.query.logId;
    if (Array.isArray(value)) return value[0] ?? null;
    return typeof value === 'string' ? value : null;
  }, [router.isReady, router.query.logId]);

  const handleRetry = () => {
    clearStartupDiagnostics();
    router.push('/startup').catch(() => undefined);
  };

  const startupFailure = isStartupFailed
    ? {
        logId,
        diagnostics: startupDiagnostics,
        onRetry: handleRetry,
      }
    : undefined;

  return <HelpView form={form} startupFailure={startupFailure} />;
};

export default HelpScreen;
