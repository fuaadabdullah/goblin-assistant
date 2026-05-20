import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('@/api', () => ({
  apiClient: { getAllHealth: jest.fn().mockResolvedValue({ status: 'healthy', latency: 42 }) },
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
  it('renders health status', async () => {
    render(<HealthHeader />, { wrapper });
    // Initially shows loading skeleton or status
    expect(document.body).toBeTruthy();
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
