"use client";

import React, { useEffect } from 'react';
import './globals.css'
import ErrorBoundary from '../src/components/ErrorBoundary'
import { ThemeProvider } from '../src/theme/components/ThemeProvider';
import { TooltipProvider } from '../src/components/ui/Tooltip';
import { initializeTheme } from '../src/theme/index';
import { I18nProvider } from '../src/i18n';

function AppProviders({ children }: { children: React.ReactNode }) {
  // Initialize theme system on mount
  useEffect(() => {
    initializeTheme();
  }, []);

  return (
    <ErrorBoundary onError={(error, errorInfo) => {
      console.error('Provider error:', error, errorInfo);
    }}>
      <I18nProvider>
        <ErrorBoundary onError={(error, errorInfo) => {
          console.error('I18nProvider error:', error, errorInfo);
        }}>
          <TooltipProvider>
            <ErrorBoundary onError={(error, errorInfo) => {
              console.error('TooltipProvider error:', error, errorInfo);
            }}>
              <ThemeProvider>
                <ErrorBoundary onError={(error, errorInfo) => {
                  console.error('ThemeProvider error:', error, errorInfo);
                }}>
                  {children}
                </ErrorBoundary>
              </ThemeProvider>
            </ErrorBoundary>
          </TooltipProvider>
        </ErrorBoundary>
      </I18nProvider>
    </ErrorBoundary>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="bg-bg-primary">
      <body className="font-mono text-text-primary bg-bg-primary">
        <ErrorBoundary onError={(error, errorInfo) => {
          console.error('Root layout error:', error, errorInfo);
        }}>
          <AppProviders>
            {children}
          </AppProviders>
        </ErrorBoundary>
      </body>
    </html>
  )
}