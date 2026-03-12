import React from 'react';
import { render, screen } from '@testing-library/react';

jest.mock('next/link', () => function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
  return <a href={href}>{children}</a>;
});
jest.mock('../../../components/Navigation', () => function MockNav() {
  return <nav data-testid="nav" />;
});
jest.mock('../../../components/Seo', () => function MockSeo() {
  return null;
});
jest.mock('../../../hooks/api/useAuthSession', () => ({
  useAuthSession: () => ({ isAuthenticated: true }),
}));
jest.mock('../../../content/brand', () => ({
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

import HomeScreen from '../HomeScreen';

describe('HomeScreen', () => {
  it('renders brand name', () => {
    render(<HomeScreen />);
    expect(screen.getByText('Goblin AI')).toBeInTheDocument();
  });

  it('renders tagline', () => {
    render(<HomeScreen />);
    expect(screen.getByText('Your AI Gateway')).toBeInTheDocument();
  });

  it('renders navigation', () => {
    render(<HomeScreen />);
    expect(screen.getByTestId('nav')).toBeInTheDocument();
  });

  it('renders gateway console link', () => {
    render(<HomeScreen />);
    const link = screen.getByText('Open Gateway Console');
    expect(link.closest('a')).toHaveAttribute('href', '/chat');
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

  it('renders gateway activity section', () => {
    render(<HomeScreen />);
    expect(screen.getByText('Gateway Activity')).toBeInTheDocument();
  });

  it('renders enterprise use cases heading', () => {
    render(<HomeScreen />);
    expect(screen.getByText('Enterprise Use Cases')).toBeInTheDocument();
  });
});
