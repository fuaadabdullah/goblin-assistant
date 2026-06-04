import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('@/lib/api/runtimeClient', () => ({
  runtimeClient: {
    getCostSummary: jest.fn(),
  },
}));
jest.mock('@/hooks/useSystemStatus', () => ({
  useSystemStatus: jest.fn(() => ({
    status: { models: 'ok', routing: 'degraded', sandbox: 'down' },
  })),
}));
jest.mock('@/hooks/useDashboardData', () => ({
  useDashboardData: jest.fn(() => ({
    dashboard: {
      cost: { total: 0.24, today: 0.02, thisMonth: 0.24, byProvider: {} },
    },
  })),
}));

jest.mock(
  '@/components/cost/CostBreakdownChart',
  () =>
    function MockCostChart({ data }: { data: unknown[] }) {
      return <div data-testid="cost-chart">{JSON.stringify(data)}</div>;
    }
);
jest.mock(
  '@/components/cost/ProviderUsageChart',
  () =>
    function MockUsageChart({ data, metric }: { data: unknown[]; metric: string }) {
      return (
        <div data-testid="usage-chart" data-metric={metric}>
          {JSON.stringify(data)}
        </div>
      );
    }
);
jest.mock('@/components/cost/chartPalette', () => ({
  getChartPaletteColor: (i: number) => ['#f00', '#0f0', '#00f'][i] || '#999',
}));

import DashboardContent from '../Dashboard';
import { runtimeClient } from '@/lib/api/runtimeClient';

const mockGetCostSummary = runtimeClient.getCostSummary as jest.Mock;

function renderWithClient(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('DashboardContent', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('renders loading skeleton initially', () => {
    mockGetCostSummary.mockReturnValue(new Promise(() => {})); // never resolves
    const { container } = renderWithClient(<DashboardContent />);
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  it('renders Dashboard heading', () => {
    mockGetCostSummary.mockReturnValue(new Promise(() => {}));
    renderWithClient(<DashboardContent />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('renders charts when data loads', async () => {
    mockGetCostSummary.mockResolvedValue({
      cost_by_provider: { openai: 12.5, anthropic: 8.3 },
      requests_by_provider: { openai: 100, anthropic: 50 },
    });
    renderWithClient(<DashboardContent />);
    const chart = await screen.findByTestId('cost-chart');
    expect(chart).toBeInTheDocument();
    const usage = await screen.findByTestId('usage-chart');
    expect(usage).toBeInTheDocument();
  });

  it('shows error on query failure', async () => {
    mockGetCostSummary.mockRejectedValue(new Error('network fail'));
    renderWithClient(<DashboardContent />);
    // TristateWrapper renders errorTitle and message in separate elements
    await screen.findByText('Failed to load data');
    expect(screen.getByText('network fail')).toBeInTheDocument();
  });

  it('renders cost data with correct colors', async () => {
    mockGetCostSummary.mockResolvedValue({
      cost_by_provider: { openai: 10 },
      requests_by_provider: {},
    });
    renderWithClient(<DashboardContent />);
    const chart = await screen.findByTestId('cost-chart');
    expect(chart.textContent).toContain('openai');
    expect(chart.textContent).toContain('#f00');
  });

  it('uses requests metric when requests data exists', async () => {
    mockGetCostSummary.mockResolvedValue({
      cost_by_provider: { openai: 10 },
      requests_by_provider: { openai: 100 },
    });
    renderWithClient(<DashboardContent />);
    const usage = await screen.findByTestId('usage-chart');
    expect(usage.getAttribute('data-metric')).toBe('requests');
  });

  it('shows empty state and zero metrics when no provider data exists', async () => {
    mockGetCostSummary.mockResolvedValue({
      cost_by_provider: {},
      requests_by_provider: {},
    });
    renderWithClient(<DashboardContent />);
    expect((await screen.findAllByText('No usage data yet')).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('$0.0000')).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Total Requests 0' })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Active Providers 0' })).toBeInTheDocument();
    expect(
      screen.getByText('Provider usage has not been recorded for this workspace.')
    ).toBeInTheDocument();
  });

  it('falls back to cost metric when no requests data', async () => {
    mockGetCostSummary.mockResolvedValue({
      cost_by_provider: { openai: 10 },
    });
    renderWithClient(<DashboardContent />);
    const usage = await screen.findByTestId('usage-chart');
    expect(usage.getAttribute('data-metric')).toBe('cost');
  });

  it('renders period filter and derived activity timeline', async () => {
    mockGetCostSummary.mockResolvedValue({
      cost_by_provider: { openai: 10, anthropic: 5, groq: 2 },
      requests_by_provider: { openai: 100, anthropic: 50, groq: 25 },
    });
    renderWithClient(<DashboardContent />);
    expect(await screen.findByText('Recent Activity')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '7d' })).toHaveAttribute('aria-pressed', 'true');
    expect(await screen.findByText('Openai cost tracked')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '30d' }));
    expect(screen.getByRole('button', { name: '30d' })).toHaveAttribute('aria-pressed', 'true');
    expect(await screen.findByText('Groq cost tracked')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'All' }));
    expect(screen.getByText('Models status: ok')).toBeInTheDocument();
  });

  it('shows onboarding prompt until onboarding is complete', async () => {
    mockGetCostSummary.mockResolvedValue({
      cost_by_provider: { openai: 10 },
      requests_by_provider: { openai: 100 },
    });
    renderWithClient(<DashboardContent />);
    expect(await screen.findByText('Finish first-run setup')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open onboarding' })).toHaveAttribute(
      'href',
      '/onboarding'
    );
  });

  it('hides onboarding prompt after completion', async () => {
    localStorage.setItem('goblinos-onboarding-complete', 'true');
    mockGetCostSummary.mockResolvedValue({
      cost_by_provider: { openai: 10 },
      requests_by_provider: { openai: 100 },
    });
    renderWithClient(<DashboardContent />);
    await screen.findByTestId('cost-chart');
    expect(screen.queryByText('Finish first-run setup')).not.toBeInTheDocument();
  });
});
