import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('@/hooks/api/useSettings', () => ({
  useProviderSettings: jest.fn(),
  ProviderConfig: {} as never,
}));
jest.mock('@/hooks/api/useHealth', () => ({
  useRoutingHealth: jest.fn(),
  RoutingHealthStatus: {} as never,
}));
jest.mock('@/components/TwoColumnLayout', () => function MockLayout({ sidebar, children }: { sidebar: React.ReactNode; children: React.ReactNode }) {
  return <div data-testid="layout"><div data-testid="sidebar">{sidebar}</div><div data-testid="main">{children}</div></div>;
});
jest.mock('@/components/ui', () => ({
  Button: ({ children, ...p }: { children: React.ReactNode; onClick?: () => void }) => <button {...p}>{children}</button>,
  Alert: ({ children }: { children: React.ReactNode }) => <div data-testid="alert">{children}</div>,
}));
jest.mock('../components/ProviderSidebar', () => function MockSidebar() { return <div data-testid="provider-sidebar" />; });
jest.mock('../components/ProviderDetails', () => function MockDetails() { return <div data-testid="provider-details" />; });
jest.mock('../components/ProviderPromptTest', () => function MockPromptTest() { return <div data-testid="prompt-test" />; });
jest.mock('../components/ProviderTestResultBanner', () => function MockBanner() { return <div data-testid="test-banner" />; });
jest.mock('../hooks/useProviderMutations', () => ({
  useProviderMutations: () => ({ testing: null, testResult: null, setTestResult: jest.fn(), quickTest: jest.fn(), promptTest: jest.fn(), setPriority: jest.fn(), reorderProviders: jest.fn(), isReordering: false }),
}));
jest.mock('../hooks/useProviderReorder', () => ({
  useProviderReorder: () => ({ draggedProvider: null, onDragStart: jest.fn(), onDragOver: jest.fn(), onDrop: jest.fn() }),
}));

import { useProviderSettings } from '@/hooks/api/useSettings';
import { useRoutingHealth } from '@/hooks/api/useHealth';
import ProvidersManagerScreen from '../ProvidersManagerScreen';

const mockUseProviderSettings = useProviderSettings as jest.Mock;
const mockUseRoutingHealth = useRoutingHealth as jest.Mock;

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('ProvidersManagerScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseProviderSettings.mockReturnValue({
      data: [{ id: 'p1', name: 'openai', enabled: true }],
      isLoading: false,
      error: null,
      refetch: jest.fn(),
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
});
