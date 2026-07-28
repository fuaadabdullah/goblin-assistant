import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockGetAllHealth = jest.fn();

jest.mock('@/api', () => ({
  apiClient: { getAllHealth: () => mockGetAllHealth() },
}));
jest.mock('../../lib/query-keys', () => ({
  queryKeys: { health: ['health'] },
}));

import HealthHeader from '../HealthHeader';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('HealthHeader', () => {
  beforeEach(() => {
    mockGetAllHealth.mockResolvedValue({
      status: 'healthy',
      timestamp: '2026-07-28T00:00:00.000Z',
      services: {},
    });
  });

  it('renders health status', async () => {
    render(<HealthHeader />, { wrapper });
    expect(await screen.findByText('OK')).toBeInTheDocument();
  });

  it('maps current backend status field', async () => {
    mockGetAllHealth.mockResolvedValueOnce({
      status: 'degraded',
      timestamp: '2026-07-28T00:00:00.000Z',
      services: {},
    });

    render(<HealthHeader />, { wrapper });

    expect(await screen.findByText('Degraded')).toBeInTheDocument();
  });

  it('maps backend warning status without showing an outage', async () => {
    mockGetAllHealth.mockResolvedValueOnce({
      status: 'warnings',
      timestamp: '2026-07-28T00:00:00.000Z',
      components: {
        providers: { status: 'degraded' },
        security: { status: 'warnings' },
      },
    });

    render(<HealthHeader />, { wrapper });

    expect(await screen.findByText('Warnings')).toBeInTheDocument();
    expect(screen.queryByText('Down')).not.toBeInTheDocument();
  });

  it('does not escalate provider-only degradation to down', async () => {
    mockGetAllHealth.mockResolvedValueOnce({
      status: 'warnings',
      timestamp: '2026-07-28T00:00:00.000Z',
      components: {
        api: { status: 'healthy' },
        routing: { status: 'healthy' },
        providers: { status: 'degraded' },
      },
    });

    render(<HealthHeader />, { wrapper });

    expect(await screen.findByText('Warnings')).toBeInTheDocument();
    expect(screen.queryByText('Down')).not.toBeInTheDocument();
  });

  it('renders in compact mode', async () => {
    render(<HealthHeader compact />, { wrapper });
    expect(await screen.findByText('OK')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<HealthHeader className="test-class" />, { wrapper });
    expect(container.firstChild).toBeTruthy();
  });
});
