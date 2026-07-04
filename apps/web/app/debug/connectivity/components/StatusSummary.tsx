'use client';

import { type FC } from 'react';
import styles from '../page.module.css';

interface StatusSummaryProps {
  chatTestResult: { status: string } | null;
  chatError: string | null;
  health: { isError: boolean; isLoading: boolean };
  isAuthenticated: boolean;
}

const StatusSummary: FC<StatusSummaryProps> = ({ chatTestResult, chatError, health, isAuthenticated }) => (
  <ul>
    <li>
      Frontend Health: <span className={styles['successText']}>✓ OK</span> (page loads and renders)
    </li>
    <li>
      Backend Health:{' '}
      {health.isLoading ? (
        <span className={styles['grayText']}>… Loading</span>
      ) : health.isError ? (
        <span className={styles['errorText']}>✗ Failed</span>
      ) : (
        <span className={styles['successText']}>✓ Connected</span>
      )}
    </li>
    <li>
      Auth Status:{' '}
      {isAuthenticated ? <span className={styles['successText']}>✓ Authenticated</span> : <span className={styles['warningText']}>⚠ Not authenticated</span>}
    </li>
    <li>
      Chat API:{' '}
      {chatError ? (
        <span className={styles['errorText']}>✗ Failed</span>
      ) : chatTestResult ? (
        <span className={styles['successText']}>✓ Connected</span>
      ) : (
        <span className={styles['grayText']}>? Not tested</span>
      )}
    </li>
  </ul>
);

export default StatusSummary;
