'use client';

import type { FC } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useSupportForm } from './hooks/useSupportForm';
import HelpView from './components/HelpView';
import type { StartupDiagnostics } from '../../utils/startup-diagnostics';
import { readStartupDiagnostics, clearStartupDiagnostics } from '../../utils/startup-diagnostics';

const HelpScreen: FC = () => {
  const form = useSupportForm();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [startupDiagnostics, setStartupDiagnostics] = useState<StartupDiagnostics | null>(null);

  const reasonParam = searchParams.get('reason');
  const logIdParam = searchParams.get('logId');

  const isStartupFailed = useMemo(() => {
    return reasonParam === 'startup_failed';
  }, [reasonParam]);

  useEffect(() => {
    if (!isStartupFailed) return;
    setStartupDiagnostics(readStartupDiagnostics());
  }, [isStartupFailed]);

  const logId = useMemo(() => {
    return logIdParam ?? null;
  }, [logIdParam]);

  const handleRetry = () => {
    clearStartupDiagnostics();
    router.push('/startup');
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
