import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

jest.mock('../ui/card', () => ({
  Card: ({ children, className }: { children: React.ReactNode; className?: string }) => <div className={className}>{children}</div>,
  CardContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardDescription: ({ children }: { children: React.ReactNode }) => <p>{children}</p>,
  CardHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardTitle: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
}));
jest.mock('../ui/Alert', () => function MockAlert({ message }: { message: string }) {
  return <div data-testid="alert">{message}</div>;
});
jest.mock('../ui', () => ({
  Button: ({ children, onClick, variant }: { children: React.ReactNode; onClick: () => void; variant?: string }) =>
    <button onClick={onClick} data-variant={variant}>{children}</button>,
}));
jest.mock('../../contexts/ToastContext', () => ({
  useToast: () => ({ showSuccess: jest.fn() }),
}));
jest.mock('../../hooks/useErrorTesting', () => ({
  useErrorTesting: jest.fn(() => ({
    isLoading: false,
    results: [],
    testJavaScriptError: jest.fn(),
    testAsyncError: jest.fn(),
    testNetworkError: jest.fn(),
    testUnhandledPromiseRejection: jest.fn(),
    testTypeError: jest.fn(),
    testCustomError: jest.fn(),
    testSentryError: jest.fn(),
    testSentryMessage: jest.fn(),
    testSentryBreadcrumb: jest.fn(),
    runAllTests: jest.fn(),
    clearResults: jest.fn(),
  })),
}));
jest.mock('../error-testing/ErrorTestButtons', () => ({
  ErrorTestButtons: function MockButtons({ running }: { running: boolean }) {
    return <div data-testid="error-test-buttons" data-running={running} />;
  },
}));
jest.mock('../error-testing/ErrorTestResults', () => ({
  ErrorTestResults: function MockResults({ results }: { results: unknown[] }) {
    return <div data-testid="error-test-results">{results.length} results</div>;
  },
}));

import { ErrorTestingPanel } from '../ErrorTestingPanel';
import { useErrorTesting } from '../../hooks/useErrorTesting';

const mockUseErrorTesting = useErrorTesting as jest.Mock;

describe('ErrorTestingPanel', () => {
  it('renders title', () => {
    render(<ErrorTestingPanel />);
    expect(screen.getByText('Error Testing Panel')).toBeInTheDocument();
  });

  it('renders description', () => {
    render(<ErrorTestingPanel />);
    expect(screen.getByText(/Generate various types of errors/)).toBeInTheDocument();
  });

  it('renders warning alerts', () => {
    render(<ErrorTestingPanel />);
    const alerts = screen.getAllByTestId('alert');
    expect(alerts.length).toBeGreaterThanOrEqual(2);
  });

  it('renders error test buttons', () => {
    render(<ErrorTestingPanel />);
    expect(screen.getByTestId('error-test-buttons')).toBeInTheDocument();
  });

  it('renders error test results', () => {
    render(<ErrorTestingPanel />);
    expect(screen.getByTestId('error-test-results')).toBeInTheDocument();
  });

  it('shows clear results button', () => {
    render(<ErrorTestingPanel />);
    expect(screen.getByText('Clear Results')).toBeInTheDocument();
  });

  it('calls clearResults on click', () => {
    const clearResults = jest.fn();
    mockUseErrorTesting.mockReturnValue({
      isLoading: false, results: [], testJavaScriptError: jest.fn(),
      testAsyncError: jest.fn(), testNetworkError: jest.fn(),
      testUnhandledPromiseRejection: jest.fn(), testTypeError: jest.fn(),
      testCustomError: jest.fn(), testSentryError: jest.fn(),
      testSentryMessage: jest.fn(), testSentryBreadcrumb: jest.fn(),
      runAllTests: jest.fn(), clearResults,
    });
    render(<ErrorTestingPanel />);
    fireEvent.click(screen.getByText('Clear Results'));
    expect(clearResults).toHaveBeenCalled();
  });

  it('passes running state to ErrorTestButtons', () => {
    mockUseErrorTesting.mockReturnValue({
      isLoading: true, results: [], testJavaScriptError: jest.fn(),
      testAsyncError: jest.fn(), testNetworkError: jest.fn(),
      testUnhandledPromiseRejection: jest.fn(), testTypeError: jest.fn(),
      testCustomError: jest.fn(), testSentryError: jest.fn(),
      testSentryMessage: jest.fn(), testSentryBreadcrumb: jest.fn(),
      runAllTests: jest.fn(), clearResults: jest.fn(),
    });
    render(<ErrorTestingPanel />);
    expect(screen.getByTestId('error-test-buttons')).toHaveAttribute('data-running', 'true');
  });
});
