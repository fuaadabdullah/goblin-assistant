import React from 'react';
import { render, screen } from '@testing-library/react';

vi.mock(
  'next/link',
  () => ({
    default: function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
      return <a href={href}>{children}</a>;
    },
  })
);
vi.mock(
  '../../../components/Navigation',
  () => ({
    default: function MockNav() {
      return <nav data-testid="nav" />;
    },
  })
);
vi.mock(
  '../../../components/Seo',
  () => ({
    default: function MockSeo() {
      return null;
    },
  })
);
vi.mock('../../../hooks/api/useAuthSession', () => ({
  useAuthSession: () => ({ isAuthenticated: true }),
}));
vi.mock('../../../content/brand', () => ({
  BRAND_NAME: 'Goblin AI',
  BRAND_TAGLINE: 'Your AI Gateway',
  HOME_EXAMPLE_CARDS: [
    { icon: '🚀', title: 'Example 1', body: 'Body 1' },
    { icon: '🔧', title: 'Example 2', body: 'Body 2' },
  ],
  HOME_VALUE_PROPS: [
    { icon: '⚡', title: 'Fast', body: 'Lightning fast' },
    { icon: '🔒', title: 'Secure', body: 'Enterprise grade' },
  ],
}));
vi.mock('../../../hooks/useSystemStatus', () => ({
  useSystemStatus: () => ({
    status: { models: 'ok', routing: 'ok', sandbox: 'ok', updatedAt: '2026-05-07T00:00:00Z' },
    loading: false,
    refresh: vi.fn(),
  }),
}));
vi.mock('../../../utils/analytics', () => ({
  trackEvent: vi.fn(),
}));
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/',
}));

import HomeScreen from '../HomeScreen';

describe('HomeScreen', () => {
  it('renders brand name', () => {
    render(<HomeScreen />);
    expect(screen.getByText('Control panel')).toBeInTheDocument();
  });

  it('renders tagline', () => {
    render(<HomeScreen />);
    expect(
      screen.getByText('Live status and quick actions — this system is running.')
    ).toBeInTheDocument();
  });

  it('renders navigation', () => {
    render(<HomeScreen />);
    expect(screen.getByTestId('nav')).toBeInTheDocument();
  });

  it('renders continue as guest link', () => {
    render(<HomeScreen />);
    const link = screen.getAllByText('Continue as guest')[0];
    expect(link.closest('a')).toHaveAttribute('href', '/chat?guest=1');
  });

  it('renders audit logs link', () => {
    render(<HomeScreen />);
    const link = screen.getByText('Audit Logs');
    expect(link.closest('a')).toHaveAttribute('href', '/search');
  });

  it('renders documentation link', () => {
    render(<HomeScreen />);
    const link = screen.getByText('Documentation');
    expect(link.closest('a')).toHaveAttribute('href', '/help');
  });

  it('renders value propositions', () => {
    render(<HomeScreen />);
    expect(screen.getByText('Fast')).toBeInTheDocument();
    expect(screen.getByText('Secure')).toBeInTheDocument();
    expect(screen.getByText('Lightning fast')).toBeInTheDocument();
  });

  it('renders example cards', () => {
    render(<HomeScreen />);
    expect(screen.getByText('Example 1')).toBeInTheDocument();
    expect(screen.getByText('Example 2')).toBeInTheDocument();
  });

  it('renders live chat demo section', () => {
    render(<HomeScreen />);
    expect(screen.getByText('Live chat demo')).toBeInTheDocument();
    expect(screen.getByText('No login. Rate limited. Instantly interactive.')).toBeInTheDocument();
    expect(screen.getByText('Open this demo')).toBeInTheDocument();
  });

  it('renders interactive demo prompt preview', () => {
    render(<HomeScreen />);
    expect(screen.getByText('Analyze a stock')).toBeInTheDocument();
    expect(
      screen.getAllByText(
        'Pull the latest data for AAPL — price, P/E, recent earnings summary, and analyst consensus.'
      )
    ).toHaveLength(2);
    expect(
      screen.getByText(
        'Goblin would fetch the latest market data, summarize the earnings trend, and highlight valuation risks before you even sign in.'
      )
    ).toBeInTheDocument();
    expect(screen.getByText('Open this demo')).toBeInTheDocument();
  });

  it('renders platform capabilities heading', () => {
    render(<HomeScreen />);
    expect(screen.getByText('Platform Capabilities')).toBeInTheDocument();
  });
});
