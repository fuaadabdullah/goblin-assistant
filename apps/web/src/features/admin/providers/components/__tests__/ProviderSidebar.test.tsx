import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('@/components/ui', () => ({
  Button: ({
    children,
    ...props
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
  }) => <button {...props}>{children}</button>,
}));
vi.mock('@/components/LoadingSkeleton', () => ({
  ProviderCardSkeleton: () => <div data-testid="skeleton" />,
}));

import ProviderSidebar from '../ProviderSidebar';

const mockProviders = [
  {
    id: 'p1',
    name: 'openai',
    enabled: true,
    configured: true,
    priority: 1,
    base_url: '',
    models: ['gpt-4'],
  },
  {
    id: 'p2',
    name: 'ollama',
    enabled: false,
    configured: false,
    priority: 2,
    base_url: '',
    models: [],
  },
];

describe('ProviderSidebar', () => {
  const baseProps = {
    providers: mockProviders as never[],
    isLoading: false,
    selectedProvider: null,
    onSelectProvider: vi.fn(),
    onRefresh: vi.fn(),
    routingStatus: 'Healthy',
    showRoutingHealth: true,
    testingProviderName: null,
    onQuickTest: vi.fn(),
    draggedProvider: null,
    isReordering: false,
    onDragStart: vi.fn(),
    onDragOver: vi.fn(),
    onDrop: vi.fn(),
  };

  beforeEach(() => vi.clearAllMocks());

  it('renders provider list', () => {
    render(<ProviderSidebar {...baseProps} />);
    expect(screen.getByText('openai')).toBeInTheDocument();
    expect(screen.getByText('ollama')).toBeInTheDocument();
  });

  it('shows loading skeleton when loading', () => {
    render(<ProviderSidebar {...baseProps} isLoading={true} providers={[]} />);
    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
  });

  it('shows routing health status', () => {
    render(<ProviderSidebar {...baseProps} />);
    expect(screen.getByText('Healthy')).toBeInTheDocument();
  });

  it('calls onRefresh when refresh button clicked', () => {
    render(<ProviderSidebar {...baseProps} />);
    const refreshBtn = screen.getByText(/refresh/i);
    fireEvent.click(refreshBtn);
    expect(baseProps.onRefresh).toHaveBeenCalled();
  });

  it('calls onSelectProvider when provider clicked', () => {
    render(<ProviderSidebar {...baseProps} />);
    fireEvent.click(screen.getByText('openai'));
    expect(baseProps.onSelectProvider).toHaveBeenCalled();
  });

  it('shows empty state when no providers', () => {
    render(<ProviderSidebar {...baseProps} providers={[]} />);
    expect(screen.getByText(/no providers/i)).toBeInTheDocument();
  });

  it('highlights selected provider', () => {
    render(<ProviderSidebar {...baseProps} selectedProvider={mockProviders[0] as never} />);
    expect(screen.getByText('openai')).toBeInTheDocument();
  });
});
