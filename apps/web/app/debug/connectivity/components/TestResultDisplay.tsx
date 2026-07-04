'use client';

import { type FC } from 'react';
import styles from '../page.module.css';

interface TestResultDisplayProps {
  result: { status: string } | null;
  error: string | null;
}

const TestResultDisplay: FC<TestResultDisplayProps> = ({ result, error }) => {
  if (error) {
    return (
      <p className={`${styles['responseContainer']} ${styles['errorText']}`}>
        <strong>Error:</strong> {error}
      </p>
    );
  }

  if (!result) return null;

  return (
    <div className={styles['responseContainer']}>
      <p className={styles['successText']}>
        <strong>✓ Success!</strong> Received response from backend
      </p>
      <details>
        <summary>Response</summary>
        <pre>{JSON.stringify(result, null, 2)}</pre>
      </details>
    </div>
  );
};

export default TestResultDisplay;