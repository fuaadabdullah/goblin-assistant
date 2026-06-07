import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/hooks/api/useSettings', () => ({
  useProviderSettings: vi.fn(),
  ProviderConfig: {} as never,
}));
vi.mock('@/hooks/api/useHealth', () => ({
  useRoutingHealth: vi.fn(),
  RoutingHealthStatus: {} as never,
}));
vi.mock(
  '@/components/TwoColumnLayout',
  () => ({
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
  })
);
vi.mock('@/components/ui', () => ({
  Button: ({ children, ...p }: { children: React.ReactNode; onClick?: () => void }) => (
    <button {...p}>{children}</button>
  ),
  Alert: ({
    title,
    message,
    children,
  }: {
    title?: React.ReactNode;
    message?: React.ReactNode;
    children?: React.ReactNode;
  }) => (
    <div data-testid="alert">
      {title}
      {message}
      {children}
    </div>
  ),
}));
vi.mock(
  '../components/ProviderSidebar',
  () => ({
    default: function MockSidebar() {
      return <div data-testid="provider-sidebar" />;
    },
  })
);
vi.mock(
  '../components/ProviderDetails',
  () => ({
    default: function MockDetails() {
      return <div data-testid="provider-details" />;
    },
  })
);
vi.mock(
  '../components/ProviderPromptTest',
  () => ({
    default: function MockPromptTest() {
      return <div data-testid="prompt-test" />;
    },
  })
);
vi.mock(
  '../components/ProviderTestResultBanner',
  () => ({
    default: function MockBanner() {
      return <div data-testid="test-banner" />;
    },
  })
);
vi.mock('@/hooks/useProviderStatus', () => ({
  useProviderStatus: () => ({
    statuses: {},
    isLoading: false,
    error: null,
    connected: false,
  }),
}));
vi.mock('../hooks/useProviderMutations', () => ({
  useProviderMutations: () => ({
    testing: null,
    testResult: null,
    setTestResult: vi.fn(),
    quickTest: vi.fn(),
    promptTest: vi.fn(),
    setPriority: vi.fn(),
    reorderProviders: vi.fn(),
    isReordering: false,
  }),
}));
vi.mock('../hooks/useProviderReorder', () => ({
  useProviderReorder: () => ({
    draggedProvider: null,
    onDragStart: vi.fn(),
    onDragOver: vi.fn(),
    onDrop: vi.fn(),
  }),
}));
const mockGetProviderRouterConfigError = vi.fn(() => null);
vi.mock('../../../../services/provider-router', () => ({
  getProviderRouterConfigError: () => mockGetProviderRouterConfigError(),
}));

import { useProviderSettings } from '@/hooks/api/useSettings';
import { useRoutingHealth } from '@/hooks/api/useHealth';
import ProvidersManagerScreen from '../ProvidersManagerScreen';

const mockUseProviderSettings = useProviderSettings as vi.Mock;
const mockUseRoutingHealth = useRoutingHealth as vi.Mock;

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('ProvidersManagerScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseProviderSettings.mockReturnValue({
      data: [{ id: 'p1', name: 'openai', enabled: true }],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseRoutingHealth.mockReturnValue({ data: { status: 'healthy' } });
  });

  it('renders the layout', () => {
    render(<ProvidersManagerScreen />, { wrapper });
    expect(screen.getByTestId('layout')).toBeInTheDocument();
  });

  it('renders sidebar', () => {
    render(<ProvidersManagerScreen />, { wrapper });
    expect(screen.getByTestId('provider-sidebar')).toBeInTheDocument();
  });

  it('renders title', () => {
    render(<ProvidersManagerScreen />, { wrapper });
    expect(screen.getByText(/Provider Manager/i)).toBeInTheDocument();
  });

  it('shows select prompt when no provider selected', () => {
    render(<ProvidersManagerScreen />, { wrapper });
    expect(screen.getByText(/select a provider/i)).toBeInTheDocument();
  });

  it('shows a config validation banner when the generated providers json is incompatible', () => {
    mockGetProviderRouterConfigError.mockReturnValueOnce(
      new Error('providers.json: expected schema_version=1, got 99')
    );

    render(<ProvidersManagerScreen />, { wrapper });

    expect(screen.getByText(/Provider routing config is incompatible/i)).toBeInTheDocument();
    expect(screen.getByText(/expected schema_version=1/i)).toBeInTheDocument();
  });
});
