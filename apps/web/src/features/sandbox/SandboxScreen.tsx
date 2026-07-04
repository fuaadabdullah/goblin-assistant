'use client';

import type { FC } from 'react';
import { useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAuthSession } from '../../hooks/api/useAuthSession';
import { useSystemStatus } from '../../hooks/useSystemStatus';
import AuthPrompt from '../../components/auth/AuthPrompt';
import { useSandboxSession } from './hooks/useSandboxSession';
import SandboxView from './components/SandboxView';

const SandboxScreen: FC = () => {
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAuthSession();
  const { status: systemStatus, loading: systemStatusLoading } = useSystemStatus({
    pollIntervalMs: 60000,
  });
  const [showAuthPrompt, setShowAuthPrompt] = useState(false);
  const guestParam = searchParams.get('guest');
  const allowGuest = useMemo(() => {
    return guestParam === '1' || guestParam === 'true';
  }, [guestParam]);
  const isGuest = !isAuthenticated && allowGuest;
  const sandboxState = systemStatusLoading
    ? 'loading'
    : systemStatus.sandbox === 'ok'
      ? 'enabled'
      : 'disabled';
  const session = useSandboxSession({ isGuest, sandboxState });

  const requireAuthModal = () => {
    if (isAuthenticated) return true;
    setShowAuthPrompt(true);
    return false;
  };

  return (
    <>
      {showAuthPrompt && (
        <AuthPrompt
          mode="modal"
          title="Sign in to save sandbox runs"
          message="Guest runs are temporary. Sign in to keep your history and logs."
          allowGuest
          onClose={() => setShowAuthPrompt(false)}
        />
      )}
      <SandboxView
        session={session}
        isGuest={isGuest}
        sandboxState={sandboxState}
        onRequireAuth={requireAuthModal}
      />
    </>
  );
};

export default SandboxScreen;
