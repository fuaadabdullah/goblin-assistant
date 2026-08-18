import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('next/link', () => function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
  return <a href={href}>{children}</a>;
});
jest.mock('lucide-react', () => new Proxy({}, {
  get: (_, name) => {
    if (name === '__esModule') return true;
    return (props: Record<string, unknown>) => <span data-testid={`icon-${String(name)}`} {...props} />;
  },
}));
jest.mock('@/components/LoadingSkeleton', () => ({
  DashboardSkeleton: () => <div data-testid="dashboard-skeleton" />,
}));
jest.mock('@/hooks/useDashboardData', () => ({
  useDashboardData: jest.fn(),
}));

// Mock child components
jest.mock('@/components/dashboard/DashboardHeader', () => ({ DashboardHeader: function MockDashHeader() { return <div data-testid="dashboard-header" />; } }));
jest.mock('@/components/dashboard/CostOverviewBanner', () => ({ CostOverviewBanner: function MockCostBanner() { return <div data-testid="cost-banner" />; } }));
jest.mock('@/components/dashboard/StatusCardsGrid', () => ({ StatusCardsGrid: function MockStatusGrid() { return <div data-testid="status-grid" />; } }));
jest.mock('@/components/dashboard/DashboardError', () => ({ DashboardError: function MockDashError({ onRetry }: { onRetry?: () => void }) {
  return <div data-testid="dashboard-error"><button onClick={onRetry}>Retry</button></div>;
} }));
jest.mock('@/components/ui', () => ({
  Grid: ({ children }: { children: React.ReactNode }) => <div data-testid="grid">{children}</div>,
}));

import EnhancedDashboard from '@/components/EnhancedDashboard';
import { useDashboardData } from '@/hooks/useDashboardData';

const mockUseDashboardData = useDashboardData as jest.Mock;

describe('EnhancedDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseDashboardData.mockReturnValue({
      dashboard: {
        cost: { total: 100, today: 1.25, thisMonth: 50, byProvider: {} },
        backend: { status: 'healthy' },
        chroma: { status: 'healthy' },
        mcp: { status: 'healthy' },
        rag: { status: 'healthy' },
        sandbox: { status: 'healthy' },
      },
      loading: false,
      error: null,
      refresh: jest.fn(),
    });
  });

  it('renders dashboard when data is loaded', () => {
    render(<EnhancedDashboard />);
    expect(screen.getByRole('heading', { name: 'Operations' })).toBeInTheDocument();
    expect(screen.getByTestId('status-grid')).toBeInTheDocument();
  });

  it('shows skeleton when loading', () => {
    mockUseDashboardData.mockReturnValue({ dashboard: null, loading: true, error: null, refresh: jest.fn() });
    render(<EnhancedDashboard />);
    expect(screen.getByTestId('dashboard-skeleton')).toBeInTheDocument();
  });

  it('shows error state when error and no dashboard', () => {
    mockUseDashboardData.mockReturnValue({
      dashboard: null,
      loading: false,
      error: new Error('fail'),
      refresh: jest.fn(),
    });
    render(<EnhancedDashboard />);
    expect(screen.getByTestId('dashboard-error')).toBeInTheDocument();
  });

  it('renders action links', () => {
    render(<EnhancedDashboard />);
    expect(screen.getByText(/chat/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /kpi dashboard/i })).toHaveAttribute('href', '/admin/kpi');
    expect(screen.getByRole('link', { name: /pilot kit/i })).toHaveAttribute('href', '/admin/pilot');
    expect(screen.getByRole('link', { name: /dogfood journal/i })).toHaveAttribute('href', '/admin/dogfood');
  });

  it('renders cost banner', () => {
    render(<EnhancedDashboard />);
    expect(screen.getByText(/cost by provider/i)).toBeInTheDocument();
  });
});
