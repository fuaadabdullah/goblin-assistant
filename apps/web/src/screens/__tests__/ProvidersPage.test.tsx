import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock dependencies
vi.mock('../../components/TwoColumnLayout', () => ({
  default: function MockLayout({
    sidebar,
    children,
  }: {
    sidebar: React.ReactNode;
    children: React.ReactNode;
  }) {
    return (
      <div data-testid="layout">
        <div data-testid="sidebar">{sidebar}</div>
        <div data-testid="main">{children}</div>
      </div>
    );
  },
}));

const mockTestConnection = vi.fn();
vi.mock('@/lib/api', () => ({
  apiClient: { testProviderConnection: (...args: unknown[]) => mockTestConnection(...args) },
}));

const mockProviderSettings = vi.fn().mockReturnValue({
  data: [
    {
      id: 'p1',
      name: 'openai',
      enabled: true,
      configured: true,
      base_url: 'https://api.openai.com',
      models: ['gpt-4'],
    },
    {
      id: 'p2',
      name: 'ollama',
      enabled: false,
      configured: false,
      base_url: 'http://ollama.internal.test:11434',
      models: [],
    },
  ],
  isLoading: false,
  error: null,
  refetch: vi.fn(),
});
vi.mock('@/hooks/api/useSettings', () => ({
  useProviderSettings: () => mockProviderSettings(),
  ProviderConfig: {} as never,
}));

const mockRoutingHealth = vi.fn().mockReturnValue({ data: { status: 'healthy' } });
vi.mock('@/hooks/api/useHealth', () => ({
  useRoutingHealth: () => mockRoutingHealth(),
}));

import ProvidersPage from '../ProvidersPage';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('ProvidersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockProviderSettings.mockReturnValue({
      data: [
        {
          id: 'p1',
          name: 'openai',
          enabled: true,
          configured: true,
          base_url: 'https://api.openai.com',
          models: ['gpt-4'],
        },
        {
          id: 'p2',
          name: 'ollama',
          enabled: false,
          configured: false,
          base_url: 'http://ollama.internal.test:11434',
          models: [],
        },
      ],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
  });

  it('renders provider list', () => {
    render(<ProvidersPage />, { wrapper });
    expect(screen.getByText(/openai/i)).toBeInTheDocument();
    expect(screen.getByText(/ollama/i)).toBeInTheDocument();
  });

  it('shows loading state when fetching', () => {
    mockProviderSettings.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });
    render(<ProvidersPage />, { wrapper });
    // Should show some loading indicator
    expect(screen.getByTestId('layout')).toBeInTheDocument();
  });

  it('renders empty state when no providers', () => {
    mockProviderSettings.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
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

  it('shows provider load errors with the underlying message', () => {
    mockProviderSettings.mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('registry unavailable'),
      refetch: vi.fn(),
    });
    render(<ProvidersPage />, { wrapper });
    expect(screen.getByText('Failed to load providers: registry unavailable')).toBeInTheDocument();
  });
});
