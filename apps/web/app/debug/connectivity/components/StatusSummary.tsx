'use client';

import { type FC } from 'react';
import styles from '../page.module.css';

interface StatusSummaryProps {
  chatTestResult: { status: string } | null;
  health: { isError: boolean };
  isAuthenticated: boolean;
}

const StatusSummary: FC<StatusSummaryProps> = ({ chatTestResult, health, isAuthenticated }) => (
  <ul>
    <li>
      Frontend Health: <span className={styles['successText']}>✓ OK</span> (page loads and renders)
    </li>
    <li>
      Backend Health:{' '}
      {health.isError ? <span className={styles['errorText']}>✗ Failed</span> : <span className={styles['successText']}>✓ Connected</span>}
    </li>
    <li>
      Auth Status:{' '}
      {isAuthenticated ? <span className={styles['successText']}>✓ Authenticated</span> : <span className={styles['warningText']}>⚠ Not authenticated</span>}
    </li>
    <li>
      Chat API:{' '}
      {chatTestResult ? <span className={styles['successText']}>✓ Connected</span> : <span className={styles['grayText']}>? Not tested</span>}
    </li>
  </ul>
);

export default StatusSummary;