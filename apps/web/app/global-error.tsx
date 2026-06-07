'use client';

// Global error boundary for the root layout.
// This is the LAST-RESORT boundary: it must NOT import any external
// components, hooks, or providers, because those may have caused the crash
// in the first place. Everything in this file is self-contained.

import { useEffect, useState } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [errorId] = useState(() => crypto.randomUUID?.() ?? 'unknown');

  useEffect(() => {
    // Send to monitoring endpoint
    fetch('/api/errors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: error.message,
        stack: error.stack,
        digest: error.digest,
        errorId,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
      }),
    }).catch(() => {
      // Silent fail — don't crash further
    });
  }, [error, errorId]);

  return (
    <html lang="en">
      <body style={{ margin: 0, backgroundColor: '#0b0907', color: '#cdc2b0' }}>
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
            fontFamily:
              '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
          }}
        >
          <div
            style={{
              maxWidth: '480px',
              width: '100%',
              backgroundColor: '#1a1713',
              border: '1px solid #2c271f',
              borderRadius: '16px',
              padding: '24px',
              boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
            }}
          >
            <div
              style={{
                width: '48px',
                height: '48px',
                margin: '0 auto 16px',
                backgroundColor: 'rgba(219, 68, 55, 0.15)',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#db4437" strokeWidth="2">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>

            <h1 style={{ fontSize: '20px', fontWeight: 600, textAlign: 'center', color: '#e6dccc', margin: '0 0 8px' }}>
              Goblin Assistant encountered a critical error
            </h1>

            <p style={{ textAlign: 'center', color: '#8a7f6e', margin: '0 0 20px', fontSize: '14px' }}>
              The application crashed before the interface could fully load.
            </p>

            <details style={{ marginBottom: '16px', fontSize: '13px' }}>
              <summary style={{ cursor: 'pointer', color: '#cdc2b0', fontWeight: 500, marginBottom: '8px' }}>
                Technical details
              </summary>
              <div
                style={{
                  backgroundColor: '#0b0907',
                  border: '1px solid #2c271f',
                  borderRadius: '8px',
                  padding: '12px',
                  overflow: 'auto',
                  fontSize: '12px',
                  color: '#cdc2b0',
                }}
              >
                <p style={{ margin: '0 0 8px' }}>
                  Reference ID: <code style={{ fontFamily: 'monospace' }}>{errorId}</code>
                </p>
                <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0 }}>
                  {error.message}
                </pre>
              </div>
            </details>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => reset()}
                style={{
                  flex: 1,
                  padding: '10px 16px',
                  borderRadius: '8px',
                  border: 'none',
                  backgroundColor: '#5b3e2b',
                  color: '#e6dccc',
                  fontSize: '14px',
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                Try Again
              </button>
              <button
                onClick={() => { window.location.href = '/'; }}
                style={{
                  flex: 1,
                  padding: '10px 16px',
                  borderRadius: '8px',
                  border: '1px solid #2c271f',
                  backgroundColor: '#1a1713',
                  color: '#cdc2b0',
                  fontSize: '14px',
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                Go Home
              </button>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}