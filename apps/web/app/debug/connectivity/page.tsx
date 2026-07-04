'use client';

import { type FC } from 'react';
import { useAuthSession } from '@/hooks/api/useAuthSession';
import AuthStatus from './components/AuthStatus';
import EndpointTester from './components/EndpointTester';
import HealthStatusDisplay from './components/HealthStatusDisplay';
import TestResultDisplay from './components/TestResultDisplay';
import StatusSummary from './components/StatusSummary';
import { useEndpointTests } from './hooks/useEndpointTests';
import styles from './page.module.css';
import type { User } from '@/types/api';

const ConnectivityDebug: FC = () => {
  const { user, isAuthenticated, isLoading: authLoading } = useAuthSession();
  const { health, chatTestResult, chatError, handleFetchConversations, handleValidateToken, handleAuthLogout } = useEndpointTests();

  // User is already the correct type from useAuthSession
  const userDisplay = user as User | null;

  return (
    <div className={styles['container']}>
      <h1>Frontend ↔ Backend Connectivity Debug</h1>

      {/* Auth Status Section */}
      <section className={styles['section']}>
        <AuthStatus
          token={null}
          user={userDisplay}
          isAuthenticated={isAuthenticated}
          isLoading={authLoading}
        />
      </section>

      {/* Health Status */}
      <section className={styles['section']}>
        <h2>Health Status</h2>
        <HealthStatusDisplay health={health} />
      </section>

      {/* Chat Endpoint Test */}
      <section className={styles['section']}>
        <h2>Chat Endpoint Test (Authenticated)</h2>
        <EndpointTester
          name="Fetch Conversations"
          endpoint="/api/v1/chat/conversations"
          requiresAuth
          onTest={handleFetchConversations}
        />
        <TestResultDisplay result={chatTestResult} error={chatError} />
      </section>

      {/* Auth Endpoint Tests */}
      <section className={styles['section']}>
        <h2>Auth Endpoints</h2>
        <div className={styles['endpointGroup']}>
          <EndpointTester
            name="Validate Token"
            endpoint="/api/auth/validate"
            requiresAuth
            onTest={handleValidateToken}
          />
          <EndpointTester
            name="Logout"
            endpoint="/api/v1/auth/logout"
            requiresAuth
            onTest={handleAuthLogout}
          />
        </div>
      </section>

      {/* Status Summary */}
      <section className={styles['sectionSummary']}>
        <h3>Summary</h3>
        <StatusSummary chatTestResult={chatTestResult} health={health} isAuthenticated={isAuthenticated} />
      </section>
    </div>
  );
};

export default ConnectivityDebug;