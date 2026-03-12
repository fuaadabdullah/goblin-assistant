import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock apiClient
const mockGetRaptorLogs = jest.fn();
jest.mock('@/api', () => ({
  apiClient: { getRaptorLogs: (...args: unknown[]) => mockGetRaptorLogs(...args) },
}));

// Mock sub-components
jest.mock('../../components/TwoColumnLayout', () => {
  return function MockTwoColumnLayout({ sidebar, children }: { sidebar: React.ReactNode; children: React.ReactNode }) {
    return <div data-testid="two-col"><div data-testid="sidebar">{sidebar}</div><div data-testid="main">{children}</div></div>;
  };
});
jest.mock('../../components/LoadingSkeleton', () => ({
  ListSkeleton: ({ count }: { count: number }) => <div data-testid="skeleton">{count} items</div>,
}));

import LogsPageContent from '../LogsPage';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('LogsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading skeleton initially', () => {
    mockGetRaptorLogs.mockReturnValue(new Promise(() => {})); // never resolves
    render(<LogsPageContent />, { wrapper });
    expect(screen.getByTestId('skeleton')).toBeInTheDocument();
    expect(screen.getByText('System Logs')).toBeInTheDocument();
  });

  it('renders logs after successful fetch', async () => {
    mockGetRaptorLogs.mockResolvedValue({
      log_tail: '{"level":"error","service":"api","message":"Something failed","id":"1","timestamp":"2024-01-01T00:00:00Z"}\n{"level":"info","service":"raptor","message":"Service started","id":"2","timestamp":"2024-01-01T00:01:00Z"}',
    });
    render(<LogsPageContent />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Something failed')).toBeInTheDocument();
    });
    expect(screen.getByText('Service started')).toBeInTheDocument();
  });

  it('renders empty state when no logs match filter', async () => {
    mockGetRaptorLogs.mockResolvedValue({ log_tail: '' });
    render(<LogsPageContent />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('No Logs Found')).toBeInTheDocument();
    });
  });

  it('shows error alert when fetch fails', async () => {
    mockGetRaptorLogs.mockRejectedValue(new Error('Network failure'));
    render(<LogsPageContent />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Failed to Load Logs')).toBeInTheDocument();
    });
  });

  it('filters logs by level', async () => {
    mockGetRaptorLogs.mockResolvedValue({
      log_tail: '{"level":"error","service":"api","message":"Error msg","id":"1","timestamp":"2024-01-01T00:00:00Z"}\n{"level":"info","service":"api","message":"Info msg","id":"2","timestamp":"2024-01-01T00:01:00Z"}',
    });
    render(<LogsPageContent />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Error msg')).toBeInTheDocument();
    });
    // Filter to errors only
    const levelFilter = screen.getByLabelText('Log level filter');
    fireEvent.change(levelFilter, { target: { value: 'error' } });
    expect(screen.getByText('Error msg')).toBeInTheDocument();
    expect(screen.queryByText('Info msg')).not.toBeInTheDocument();
  });

  it('toggles auto-refresh checkbox', async () => {
    mockGetRaptorLogs.mockResolvedValue({ log_tail: '' });
    render(<LogsPageContent />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('No Logs Found')).toBeInTheDocument();
    });
    const checkbox = screen.getByLabelText('Auto-refresh (5s)');
    expect(checkbox).not.toBeChecked();
    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();
  });

  it('clears display when clear button clicked', async () => {
    mockGetRaptorLogs.mockResolvedValue({
      log_tail: '{"level":"info","service":"api","message":"Some log","id":"1","timestamp":"2024-01-01T00:00:00Z"}',
    });
    render(<LogsPageContent />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Some log')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByLabelText('Clear logs display'));
    await waitFor(() => {
      expect(screen.getByText('No Logs Found')).toBeInTheDocument();
    });
  });

  it('selects and expands a log entry with details', async () => {
    mockGetRaptorLogs.mockResolvedValue({
      log_tail: '{"level":"error","service":"api","message":"Error with details","id":"detail-1","timestamp":"2024-01-01T00:00:00Z","details":{"stack":"trace"}}',
    });
    render(<LogsPageContent />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Error with details')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Error with details'));
    expect(screen.getByText('Details:')).toBeInTheDocument();
  });

  it('parses non-JSON log lines as plain text', async () => {
    mockGetRaptorLogs.mockResolvedValue({
      log_tail: 'plain text log line',
    });
    render(<LogsPageContent />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('plain text log line')).toBeInTheDocument();
    });
  });

  it('handles service filter', async () => {
    mockGetRaptorLogs.mockResolvedValue({
      log_tail: '{"level":"info","service":"api","message":"api log","id":"1","timestamp":"2024-01-01T00:00:00Z"}\n{"level":"info","service":"worker","message":"worker log","id":"2","timestamp":"2024-01-01T00:01:00Z"}',
    });
    render(<LogsPageContent />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('api log')).toBeInTheDocument();
    });
    const serviceFilter = screen.getByLabelText('Service filter');
    fireEvent.change(serviceFilter, { target: { value: 'api' } });
    expect(screen.getByText('api log')).toBeInTheDocument();
    expect(screen.queryByText('worker log')).not.toBeInTheDocument();
  });

  it('shows statistics in sidebar', async () => {
    mockGetRaptorLogs.mockResolvedValue({
      log_tail: '{"level":"error","service":"api","message":"err","id":"1","timestamp":"2024-01-01T00:00:00Z"}\n{"level":"warning","service":"api","message":"warn","id":"2","timestamp":"2024-01-01T00:01:00Z"}',
    });
    render(<LogsPageContent />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('err')).toBeInTheDocument();
    });
    expect(screen.getByText('Statistics')).toBeInTheDocument();
  });
});
