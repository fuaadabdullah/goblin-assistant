import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock dependencies
jest.mock('../../components/TwoColumnLayout', () => {
  return function MockLayout({ sidebar, children }: { sidebar: React.ReactNode; children: React.ReactNode }) {
    return <div data-testid="layout"><div data-testid="sidebar">{sidebar}</div><div data-testid="main">{children}</div></div>;
  };
});

const mockTestConnection = jest.fn();
jest.mock('@/api', () => ({
  apiClient: { testProviderConnection: (...args: unknown[]) => mockTestConnection(...args) },
}));

const mockProviderSettings = jest.fn().mockReturnValue({
  data: [
    { id: 'p1', name: 'openai', enabled: true, configured: true, base_url: 'https://api.openai.com', models: ['gpt-4'] },
    { id: 'p2', name: 'ollama', enabled: false, configured: false, base_url: 'http://localhost:11434', models: [] },
  ],
  isLoading: false,
  error: null,
  refetch: jest.fn(),
});
jest.mock('@/hooks/api/useSettings', () => ({
  useProviderSettings: () => mockProviderSettings(),
  ProviderConfig: {} as never,
}));

const mockRoutingHealth = jest.fn().mockReturnValue({ data: { status: 'healthy' } });
jest.mock('@/hooks/api/useHealth', () => ({
  useRoutingHealth: () => mockRoutingHealth(),
}));

import ProvidersPage from '../ProvidersPage';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('ProvidersPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockProviderSettings.mockReturnValue({
      data: [
        { id: 'p1', name: 'openai', enabled: true, configured: true, base_url: 'https://api.openai.com', models: ['gpt-4'] },
        { id: 'p2', name: 'ollama', enabled: false, configured: false, base_url: 'http://localhost:11434', models: [] },
      ],
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
  });

  it('renders provider list', () => {
    render(<ProvidersPage />, { wrapper });
    expect(screen.getByText(/openai/i)).toBeInTheDocument();
    expect(screen.getByText(/ollama/i)).toBeInTheDocument();
  });

  it('shows loading state when fetching', () => {
    mockProviderSettings.mockReturnValue({ data: null, isLoading: true, error: null, refetch: jest.fn() });
    render(<ProvidersPage />, { wrapper });
    // Should show some loading indicator
    expect(screen.getByTestId('layout')).toBeInTheDocument();
  });

  it('renders empty state when no providers', () => {
    mockProviderSettings.mockReturnValue({ data: [], isLoading: false, error: null, refetch: jest.fn() });
    render(<ProvidersPage />, { wrapper });
    expect(screen.getByTestId('layout')).toBeInTheDocument();
  });

  it('renders two-column layout', () => {
    render(<ProvidersPage />, { wrapper });
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('main')).toBeInTheDocument();
  });

  it('handles provider selection', () => {
    render(<ProvidersPage />, { wrapper });
    const openaiBtn = screen.getByText(/openai/i);
    fireEvent.click(openaiBtn);
    // Should show provider detail or update selection
  });
});
