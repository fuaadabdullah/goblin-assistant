import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('next/link', () => function MockLink({ children, href, onClick }: { children: React.ReactNode; href: string; onClick?: () => void }) {
  return <a href={href} onClick={onClick}>{children}</a>;
});

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => '/',
}));

jest.mock('lucide-react', () => new Proxy({}, {
  get: (_, name) => {
    if (name === '__esModule') return true;
    return (props: Record<string, unknown>) => <span data-testid={`icon-${String(name)}`} {...props} />;
  },
}));

jest.mock('@/components/Logo', () => function MockLogo() { return <div data-testid="logo" />; });

jest.mock('../MobileDrawer', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { useUIStore } = require('../../store/uiStore');
  return function MockMobileDrawer({ children }: { children: React.ReactNode }) {
    const isOpen = useUIStore((s: { mobileNavOpen: boolean }) => s.mobileNavOpen);
    return isOpen ? <div data-testid="mobile-nav-content">{children}</div> : null;
  };
});

import Layout from '../Layout';
import { useUIStore } from '../../store/uiStore';

describe('Layout', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Storage.prototype.removeItem = jest.fn();
    useUIStore.setState({ mobileNavOpen: false });
  });

  it('renders header with logo and navigation', () => {
    render(<Layout><div>Content</div></Layout>);
    expect(screen.getByTestId('logo')).toBeInTheDocument();
    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('renders desktop nav items', () => {
    render(<Layout><div>Test</div></Layout>);
    const homeLinks = screen.getAllByText('Home');
    expect(homeLinks.length).toBeGreaterThanOrEqual(1);
    const chatLinks = screen.getAllByText('Chat');
    expect(chatLinks.length).toBeGreaterThanOrEqual(1);
    const searchLinks = screen.getAllByText('Search');
    expect(searchLinks.length).toBeGreaterThanOrEqual(1);
    const settingsLinks = screen.getAllByText('Settings');
    expect(settingsLinks.length).toBeGreaterThanOrEqual(1);
  });

  it('renders logout button', () => {
    render(<Layout><div>Test</div></Layout>);
    const logoutButtons = screen.getAllByText('Logout');
    expect(logoutButtons.length).toBeGreaterThanOrEqual(1);
  });

  it('handles logout by clearing token and navigating', () => {
    render(<Layout><div>Test</div></Layout>);
    const logoutButtons = screen.getAllByText('Logout');
    fireEvent.click(logoutButtons[0]);
    expect(localStorage.removeItem).toHaveBeenCalledWith('token');
    expect(mockPush).toHaveBeenCalledWith('/login');
  });

  it('toggles mobile menu', () => {
    const { container } = render(<Layout><div>Test</div></Layout>);
    const mobileBtn = container.querySelector('.md\\:hidden button') as HTMLButtonElement;
    expect(mobileBtn).toBeInTheDocument();
    fireEvent.click(mobileBtn);
    expect(screen.getByTestId('mobile-nav-content')).toBeInTheDocument();
  });

  it('closes mobile menu on nav click', () => {
    const { container } = render(<Layout><div>Test</div></Layout>);
    const mobileBtn = container.querySelector('.md\\:hidden button') as HTMLButtonElement;
    fireEvent.click(mobileBtn);
    expect(screen.getByTestId('mobile-nav-content')).toBeInTheDocument();
    const mobileLinks = screen.getAllByText('Chat');
    fireEvent.click(mobileLinks[mobileLinks.length - 1]);
    expect(screen.queryByTestId('mobile-nav-content')).not.toBeInTheDocument();
  });

  it('renders children in main content area', () => {
    render(<Layout><div data-testid="child">Hello</div></Layout>);
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });
});
