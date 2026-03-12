import React from 'react';
import { render, screen } from '@testing-library/react';

jest.mock('@tanstack/react-query', () => ({
  QueryClientProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock('@vercel/analytics/react', () => ({
  Analytics: () => null,
}));
jest.mock('../../contexts/ToastContext', () => ({
  ToastProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock('../../contexts/ProviderContext', () => ({
  ProviderProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock('../../hooks/useContrastMode', () => ({
  ContrastModeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock('../../auth/AuthBootstrapper', () => function MockAuthBootstrapper() {
  return <div data-testid="auth-bootstrapper" />;
});
jest.mock('../../components/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock('../../components/RouteBoundary', () => ({
  RouteBoundaryFallback: () => null,
  formatBoundaryTechnicalDetail: () => '',
}));
jest.mock('../../lib/queryClient', () => ({
  createQueryClient: () => ({}),
}));
jest.mock('../../utils/analytics', () => ({
  initGA: jest.fn(),
}));
jest.mock('../../utils/error-tracking', () => ({
  setupGlobalErrorTracking: jest.fn(),
  monitorNetworkStatus: jest.fn(),
}));
jest.mock('../../index.css', () => {});
jest.mock('highlight.js/styles/github-dark.css', () => {});

import App from '../../pages/_app';
import { initGA } from '../../utils/analytics';
import { setupGlobalErrorTracking, monitorNetworkStatus } from '../../utils/error-tracking';
import type { AppProps } from 'next/app';

function MockPage() {
  return <div data-testid="page">Page Content</div>;
}

const defaultAppProps: AppProps = {
  Component: MockPage as any,
  pageProps: {},
  router: {} as any,
};

describe('_app', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders the page component', () => {
    render(<App {...defaultAppProps} />);
    expect(screen.getByTestId('page')).toHaveTextContent('Page Content');
  });

  it('renders AuthBootstrapper', () => {
    render(<App {...defaultAppProps} />);
    expect(screen.getByTestId('auth-bootstrapper')).toBeInTheDocument();
  });

  it('renders skip-to-content link', () => {
    render(<App {...defaultAppProps} />);
    const skipLink = screen.getByText('Skip to main content');
    expect(skipLink).toHaveAttribute('href', '#main-content');
  });

  it('calls initGA on mount', () => {
    render(<App {...defaultAppProps} />);
    expect(initGA).toHaveBeenCalled();
  });

  it('calls setupGlobalErrorTracking on mount', () => {
    render(<App {...defaultAppProps} />);
    expect(setupGlobalErrorTracking).toHaveBeenCalled();
  });

  it('calls monitorNetworkStatus on mount', () => {
    render(<App {...defaultAppProps} />);
    expect(monitorNetworkStatus).toHaveBeenCalled();
  });

  it('passes pageProps to component', () => {
    function PropsPage({ customProp }: { customProp: string }) {
      return <div data-testid="props-page">{customProp}</div>;
    }
    render(<App {...defaultAppProps} Component={PropsPage as any} pageProps={{ customProp: 'hello' }} />);
    expect(screen.getByTestId('props-page')).toHaveTextContent('hello');
  });
});
