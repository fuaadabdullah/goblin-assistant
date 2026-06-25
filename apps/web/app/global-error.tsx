'use client';

// Global error boundary for the root layout.
// This is the LAST-RESORT boundary: it must NOT import any external
// components, hooks, or providers, because those may have caused the crash
// in the first place. Everything in this file is self-contained.

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import type { CSSProperties } from 'react';

const bodyStyle: CSSProperties = { margin: 0, backgroundColor: '#0b0907', color: '#cdc2b0' };
const pageStyle: CSSProperties = {
  minHeight: '100vh',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '16px',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
};
const cardStyle: CSSProperties = {
  maxWidth: '480px',
  width: '100%',
  backgroundColor: '#1a1713',
  border: '1px solid #2c271f',
  borderRadius: '16px',
  padding: '24px',
  boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
};
const iconWrapStyle: CSSProperties = {
  width: '48px',
  height: '48px',
  margin: '0 auto 16px',
  backgroundColor: 'rgba(219, 68, 55, 0.15)',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};
const titleStyle: CSSProperties = {
  fontSize: '20px',
  fontWeight: 600,
  textAlign: 'center',
  color: '#e6dccc',
  margin: '0 0 8px',
};
const subtitleStyle: CSSProperties = {
  textAlign: 'center',
  color: '#8a7f6e',
  margin: '0 0 20px',
  fontSize: '14px',
};
const detailsStyle: CSSProperties = { marginBottom: '16px', fontSize: '13px' };
const summaryStyle: CSSProperties = {
  cursor: 'pointer',
  color: '#cdc2b0',
  fontWeight: 500,
  marginBottom: '8px',
};
const detailsPanelStyle: CSSProperties = {
  backgroundColor: '#0b0907',
  border: '1px solid #2c271f',
  borderRadius: '8px',
  padding: '12px',
  overflow: 'auto',
  fontSize: '12px',
  color: '#cdc2b0',
};
const actionsStyle: CSSProperties = { display: 'flex', gap: '8px' };
const primaryButtonStyle: CSSProperties = {
  flex: 1,
  padding: '10px 16px',
  borderRadius: '8px',
  border: 'none',
  backgroundColor: '#5b3e2b',
  color: '#e6dccc',
  fontSize: '14px',
  fontWeight: 500,
  cursor: 'pointer',
};
const secondaryButtonStyle: CSSProperties = {
  flex: 1,
  padding: '10px 16px',
  borderRadius: '8px',
  border: '1px solid #2c271f',
  backgroundColor: '#1a1713',
  color: '#cdc2b0',
  fontSize: '14px',
  fontWeight: 500,
  cursor: 'pointer',
};

function CriticalErrorIcon() {
  return (
    <div style={iconWrapStyle}>
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#db4437" strokeWidth="2">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
    </div>
  );
}

function CriticalErrorDetails({
  errorId,
  error,
}: {
  errorId: string;
  error: Error & { digest?: string };
}) {
  return (
    <details style={detailsStyle}>
      <summary style={summaryStyle}>Technical details</summary>
      <div style={detailsPanelStyle}>
        <p style={{ margin: '0 0 8px' }}>
          Reference ID: <code style={{ fontFamily: 'monospace' }}>{errorId}</code>
        </p>
        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0 }}>
          {error.message}
        </pre>
      </div>
    </details>
  );
}

function CriticalErrorActions({ reset }: { reset: () => void }) {
  return (
    <div style={actionsStyle}>
      <button onClick={() => reset()} style={primaryButtonStyle}>
        Try Again
      </button>
      <button
        onClick={() => {
          window.location.href = '/';
        }}
        style={secondaryButtonStyle}
      >
        Go Home
      </button>
    </div>
  );
}

function CriticalErrorCard({
  error,
  errorId,
  reset,
}: {
  error: Error & { digest?: string };
  errorId: string;
  reset: () => void;
}) {
  return (
    <div style={pageStyle}>
      <div style={cardStyle}>
        <CriticalErrorIcon />
        <h1 style={titleStyle}>Goblin Assistant encountered a critical error</h1>
        <p style={subtitleStyle}>The application crashed before the interface could fully load.</p>
        <CriticalErrorDetails error={error} errorId={errorId} />
        <CriticalErrorActions reset={reset} />
      </div>
    </div>
  );
}

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [errorId] = useState(() => crypto.randomUUID?.() ?? 'unknown');

  useEffect(() => {
    // Send to monitoring endpoint via the API client boundary.
    void apiClient.submitErrorReport({
      message: error.message,
      stack: error.stack,
      digest: error.digest,
      errorId,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    }).catch(() => {
      // Silent fail — don't crash further
    });
  }, [error, errorId]);

  return (
    <html lang="en">
      <body style={bodyStyle}>
        <CriticalErrorCard error={error} errorId={errorId} reset={reset} />
      </body>
    </html>
  );
}
