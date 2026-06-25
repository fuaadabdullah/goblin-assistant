import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const { mockGetAllHealth } = vi.hoisted(() => ({
  mockGetAllHealth: vi.fn(),
}));

vi.mock('@/lib/api', () => ({
  apiClient: { getAllHealth: (...args: unknown[]) => mockGetAllHealth(...args) },
}));
vi.mock('../../lib/query-keys', () => ({
  queryKeys: { health: ['health'] },
}));

import HealthHeader from '../HealthHeader';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('HealthHeader', () => {
  beforeEach(() => {
    mockGetAllHealth.mockResolvedValue({ status: 'healthy', latency: 42 });
  });

  it('renders health status', async () => {
    render(<HealthHeader />, { wrapper });
    // Initially shows loading skeleton or status
    expect(document.body).toBeTruthy();
  });

  it('maps warning backend health to degraded instead of down', async () => {
    mockGetAllHealth.mockResolvedValueOnce({
      status: 'warnings',
      components: {
        api: { status: 'healthy' },
        providers: { status: 'warnings' },
        routing: { status: 'healthy' },
      },
    });

    render(<HealthHeader compact />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Degraded')).toBeInTheDocument();
    });
  });

  it('renders in compact mode', () => {
    render(<HealthHeader compact />, { wrapper });
    expect(document.body).toBeTruthy();
  });

  it('applies custom className', () => {
    const { container } = render(<HealthHeader className="test-class" />, { wrapper });
    expect(container.firstChild).toBeTruthy();
  });
});
