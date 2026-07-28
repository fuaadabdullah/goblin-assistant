'use client';

import { type FC } from 'react';
import styles from '../page.module.css';
import type { User } from '@/types/api';

const AuthStatus: FC<{
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}> = ({ token, user, isAuthenticated, isLoading }) => {
  const maskedToken = token
    ? `${token.substring(0, 8)}...${token.substring(token.length - 4)}`
    : null;

  if (isLoading) {
    return (
      <div className={styles['authSection']}>
        <h3>Auth Status</h3>
        <p>Loading auth state...</p>
      </div>
    );
  }

  return (
    <div className={styles['authSection']}>
      <h3>Auth Status</h3>
      {isAuthenticated && user ? (
        <div className={styles['authDetails']}>
          <p>
            <strong>Status:</strong>{' '}
            <span className={styles['statusHealthy']}>✓ Authenticated</span>
          </p>
          <p>
            <strong>User:</strong> {user.email || 'N/A'}
          </p>
          <p>
            <strong>Role:</strong> {user.role || 'user'}
          </p>
          <p>
            <strong>User ID:</strong> {user.id || 'N/A'}
          </p>
          {maskedToken && (
            <p>
              <strong>Token:</strong> <code className={styles['tokenDisplay']}>{maskedToken}</code>
            </p>
          )}
        </div>
      ) : (
        <p className={styles['warningText']}>
          <strong>Status:</strong> Not authenticated
        </p>
      )}
    </div>
  );
};

export default AuthStatus;
