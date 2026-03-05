import type { AppProps } from 'next/app';
import { useState } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { Analytics } from '@vercel/analytics/react';
import { ToastProvider } from '../contexts/ToastContext';
import { ProviderProvider } from '../contexts/ProviderContext';
import { ContrastModeProvider } from '../hooks/useContrastMode';
import AuthBootstrapper from '../auth/AuthBootstrapper';
import { createQueryClient } from '../lib/queryClient';

// Import global CSS files - Next.js only allows global CSS imports in _app.tsx
import '../index.css';

export default function App({ Component, pageProps }: AppProps) {
  const [queryClient] = useState(() => createQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <AuthBootstrapper />
      <ToastProvider>
        <ProviderProvider>
          <ContrastModeProvider>
            <a href="#main-content" className="skip-link">
              Skip to main content
            </a>
            <Component {...pageProps} />
            <Analytics />
          </ContrastModeProvider>
        </ProviderProvider>
      </ToastProvider>
    </QueryClientProvider>
  );
}
