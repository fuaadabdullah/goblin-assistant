import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('@/api', () => ({
  runtimeClient: {
    getCostSummary: jest.fn(),
  },
}));

jest.mock('@/components/cost/CostBreakdownChart', () => function MockCostChart({ data }: { data: unknown[] }) {
  return <div data-testid="cost-chart">{JSON.stringify(data)}</div>;
});
jest.mock('@/components/cost/ProviderUsageChart', () => function MockUsageChart({ data, metric }: { data: unknown[]; metric: string }) {
  return <div data-testid="usage-chart" data-metric={metric}>{JSON.stringify(data)}</div>;
});
jest.mock('@/components/cost/chartPalette', () => ({
  getChartPaletteColor: (i: number) => ['#f00', '#0f0', '#00f'][i] || '#999',
}));

import DashboardContent from '../Dashboard';
import { runtimeClient } from '@/api';

const mockGetCostSummary = runtimeClient.getCostSummary as jest.Mock;

function renderWithClient(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('DashboardContent', () => {
  beforeEach(() => {
    jest.clearAllMocks();
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
    const err = await screen.findByText(/Error loading data.*network fail/);
    expect(err).toBeInTheDocument();
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

  it('falls back to cost metric when no requests data', async () => {
    mockGetCostSummary.mockResolvedValue({
      cost_by_provider: { openai: 10 },
    });
    renderWithClient(<DashboardContent />);
    const usage = await screen.findByTestId('usage-chart');
    expect(usage.getAttribute('data-metric')).toBe('cost');
  });
});
