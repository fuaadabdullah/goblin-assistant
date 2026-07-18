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

  const status = health.data.overall ?? health.data.status ?? 'unknown';
  const statusClass =
    status === 'healthy'
      ? styles['statusHealthy']
      : status === 'warnings' || status === 'degraded'
        ? styles['warningText']
        : styles['statusUnhealthy'];

  return (
    <div>
      <p>
        <strong>Status:</strong>{' '}
        <span className={statusClass}>{status}</span>
      </p>
      {health.data.timestamp ? (
        <p>
          <strong>Timestamp:</strong> {health.data.timestamp}
        </p>
      ) : null}
      <details>
        <summary>Full Response</summary>
        <pre>{JSON.stringify(health.data, null, 2)}</pre>
      </details>
    </div>
  );
};

export default HealthStatusDisplay;
