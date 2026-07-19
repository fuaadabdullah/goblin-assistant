'use client';

import { type FC } from 'react';
import styles from '../page.module.css';
import type { HealthStatus } from '@/types/api';

interface HealthStatusDisplayProps {
  health: {
    isLoading: boolean;
    isError: boolean;
    data: HealthStatus | undefined;
    error: unknown;
  };
}

const HealthStatusDisplay: FC<HealthStatusDisplayProps> = ({ health }) => {
  if (health.isLoading) return <p>Loading health status...</p>;

  if (health.isError) {
    return (
      <p className={styles['errorText']}>
        Error: {health.error instanceof Error ? health.error.message : String(health.error)}
      </p>
    );
  }

  if (!health.data) return null;

  return (
    <div>
      <p>
        <strong>Status:</strong>{' '}
        <span
          className={
            health.data.overall === 'healthy' ? styles['statusHealthy'] : styles['statusUnhealthy']
          }
        >
          {health.data.overall || 'unknown'}
        </span>
      </p>
      <p>
        <strong>Timestamp:</strong> {health.data.timestamp}
      </p>
      <details>
        <summary>Full Response</summary>
        <pre>{JSON.stringify(health.data, null, 2)}</pre>
      </details>
    </div>
  );
};

export default HealthStatusDisplay;
