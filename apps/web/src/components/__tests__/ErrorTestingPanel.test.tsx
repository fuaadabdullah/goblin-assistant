import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('../ui/card', () => ({
  Card: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
  CardContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardDescription: ({ children }: { children: React.ReactNode }) => <p>{children}</p>,
  CardHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardTitle: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
}));
vi.mock('../ui/Alert', () => ({
  default: function MockAlert({ message }: { message: string }) {
    return <div data-testid="alert">{message}</div>;
  },
}));
vi.mock('../ui', () => ({
  Button: ({
    children,
    onClick,
    variant,
  }: {
    children: React.ReactNode;
    onClick: () => void;
    variant?: string;
  }) => (
    <button onClick={onClick} data-variant={variant}>
      {children}
    </button>
  ),
}));
vi.mock('../../hooks/useToast', () => ({
  useToast: () => ({ showSuccess: vi.fn() }),
}));
vi.mock('../../hooks/useErrorTesting', () => ({
  useErrorTesting: vi.fn(() => ({
    isLoading: false,
    results: [],
    testJavaScriptError: vi.fn(),
    testAsyncError: vi.fn(),
    testNetworkError: vi.fn(),
    testUnhandledPromiseRejection: vi.fn(),
    testTypeError: vi.fn(),
    testCustomError: vi.fn(),
    testSentryError: vi.fn(),
    testSentryMessage: vi.fn(),
    testSentryBreadcrumb: vi.fn(),
    runAllTests: vi.fn(),
    clearResults: vi.fn(),
  })),
}));
vi.mock('../error-testing/ErrorTestButtons', () => ({
  ErrorTestButtons: function MockButtons({ running }: { running: boolean }) {
    return <div data-testid="error-test-buttons" data-running={running} />;
  },
}));
vi.mock('../error-testing/ErrorTestResults', () => ({
  ErrorTestResults: function MockResults({ results }: { results: unknown[] }) {
    return <div data-testid="error-test-results">{results.length} results</div>;
  },
}));

import { ErrorTestingPanel } from '../ErrorTestingPanel';
import { useErrorTesting } from '../../hooks/useErrorTesting';

const mockUseErrorTesting = useErrorTesting as vi.Mock;

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
    const clearResults = vi.fn();
    mockUseErrorTesting.mockReturnValue({
      isLoading: false,
      results: [],
      testJavaScriptError: vi.fn(),
      testAsyncError: vi.fn(),
      testNetworkError: vi.fn(),
      testUnhandledPromiseRejection: vi.fn(),
      testTypeError: vi.fn(),
      testCustomError: vi.fn(),
      testSentryError: vi.fn(),
      testSentryMessage: vi.fn(),
      testSentryBreadcrumb: vi.fn(),
      runAllTests: vi.fn(),
      clearResults,
    });
    render(<ErrorTestingPanel />);
    fireEvent.click(screen.getByText('Clear Results'));
    expect(clearResults).toHaveBeenCalled();
  });

  it('passes running state to ErrorTestButtons', () => {
    mockUseErrorTesting.mockReturnValue({
      isLoading: true,
      results: [],
      testJavaScriptError: vi.fn(),
      testAsyncError: vi.fn(),
      testNetworkError: vi.fn(),
      testUnhandledPromiseRejection: vi.fn(),
      testTypeError: vi.fn(),
      testCustomError: vi.fn(),
      testSentryError: vi.fn(),
      testSentryMessage: vi.fn(),
      testSentryBreadcrumb: vi.fn(),
      runAllTests: vi.fn(),
      clearResults: vi.fn(),
    });
    render(<ErrorTestingPanel />);
    expect(screen.getByTestId('error-test-buttons')).toHaveAttribute('data-running', 'true');
  });
});
