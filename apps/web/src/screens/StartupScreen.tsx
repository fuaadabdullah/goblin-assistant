'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import GoblinBootScreen from '../features/startup/components/GoblinBootScreen';
import { useStartupFlow } from '../features/startup/hooks/useStartupFlow';

const StartupScreen = () => {
  const router = useRouter();
  const { status, message, destinationRoute } = useStartupFlow();

  useEffect(() => {
    if (!destinationRoute) return;
    router.prefetch(destinationRoute);
  }, [destinationRoute, router]);

  useEffect(() => {
    if (status !== 'ready' || !destinationRoute) return;
    router.replace(destinationRoute);
  }, [destinationRoute, router, status]);

  useEffect(() => {
    if (status !== 'error' || !destinationRoute) return;
    router.replace(destinationRoute);
  }, [destinationRoute, router, status]);

  return <GoblinBootScreen status={status} message={message} />;
};

export default StartupScreen;
