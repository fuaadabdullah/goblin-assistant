import type { FC } from 'react';
import { useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuthStore } from '../../store/authStore';
import AuthPrompt from '../../components/Auth/AuthPrompt';
import { useSandboxSession } from './hooks/useSandboxSession';
import SandboxView from './components/SandboxView';

const SandboxScreen: FC = () => {
  const router = useRouter();
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  const [showAuthPrompt, setShowAuthPrompt] = useState(false);
  const allowGuest = useMemo(() => {
    if (!router.isReady) return false;
    return router.query.guest === '1' || router.query.guest === 'true';
  }, [router.isReady, router.query.guest]);
  const isGuest = !isAuthenticated && allowGuest;
  const session = useSandboxSession({ isGuest });

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
        onRequireAuth={requireAuthModal}
      />
    </>
  );
};

export default SandboxScreen;
