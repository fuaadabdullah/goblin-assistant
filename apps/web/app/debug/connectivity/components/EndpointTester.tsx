'use client';

import { useState, type FC } from 'react';
import styles from '../page.module.css';

interface EndpointTesterProps {
  name: string;
  endpoint: string;
  requiresAuth?: boolean;
  onTest: () => Promise<void>;
}

const EndpointTester: FC<EndpointTesterProps> = ({
  name,
  endpoint,
  requiresAuth = false,
  onTest,
}) => {
  const [response, setResponse] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleTest = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      await onTest();
      setResponse({ status: 'success' });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles['endpointTester']}>
      <button className={styles['button']} onClick={handleTest} disabled={loading} type="button">
        {loading ? 'Testing...' : `Test ${name}`}
      </button>
      {requiresAuth && <span className={styles['authBadge']}>Auth Required</span>}

      {error && (
        <p className={`${styles['responseContainer']} ${styles['errorText']}`}>
          <strong>Error:</strong> {error}
        </p>
      )}

      {response && (
        <div className={styles['responseContainer']}>
          <p className={styles['successText']}>
            <strong>✓ Success!</strong>
          </p>
          <details>
            <summary>Response</summary>
            <pre>{JSON.stringify(response, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
};

export default EndpointTester;
