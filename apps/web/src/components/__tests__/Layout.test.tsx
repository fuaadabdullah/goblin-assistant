import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock(
  'next/link',
  () =>
    function MockLink({
      children,
      href,
      onClick,
    }: {
      children: React.ReactNode;
      href: string;
      onClick?: () => void;
    }) {
      return (
        <a href={href} onClick={onClick}>
          {children}
        </a>
      );
    }
);

const mockPush = jest.fn();
jest.mock('next/router', () => ({
  useRouter: () => ({ pathname: '/', push: mockPush, events: { on: jest.fn(), off: jest.fn() } }),
}));

jest.mock(
  'lucide-react',
  () =>
    new Proxy(
      {},
      {
        get: (_, name) => {
          if (name === '__esModule') return true;
          return (props: Record<string, unknown>) => (
            <span data-testid={`icon-${String(name)}`} {...props} />
          );
        },
      }
    )
);

jest.mock(
  '@/components/Logo',
  () =>
    function MockLogo() {
      return <div data-testid="logo" />;
    }
);

import Layout from '../Layout';

describe('Layout', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Storage.prototype.removeItem = jest.fn();
  });

  it('renders header with logo and navigation', () => {
    render(
      <Layout>
        <div>Content</div>
      </Layout>
    );
    expect(screen.getByTestId('logo')).toBeInTheDocument();
    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('renders desktop nav items', () => {
    render(
      <Layout>
        <div>Test</div>
      </Layout>
    );
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
    render(
      <Layout>
        <div>Test</div>
      </Layout>
    );
    const logoutButtons = screen.getAllByText('Logout');
    expect(logoutButtons.length).toBeGreaterThanOrEqual(1);
  });

  it('handles logout by clearing token and navigating', () => {
    render(
      <Layout>
        <div>Test</div>
      </Layout>
    );
    const logoutButtons = screen.getAllByText('Logout');
    fireEvent.click(logoutButtons[0]);
    expect(localStorage.removeItem).toHaveBeenCalledWith('token');
    expect(mockPush).toHaveBeenCalledWith('/login');
  });

  it('toggles mobile menu', () => {
    const { container } = render(
      <Layout>
        <div>Test</div>
      </Layout>
    );
    // Mobile menu button is inside the md:hidden div
    const mobileBtn = container.querySelector('.md\\:hidden button') as HTMLButtonElement;
    expect(mobileBtn).toBeInTheDocument();
    fireEvent.click(mobileBtn);
    // After click, mobile drawer is rendered via MobileDrawer (portal-based with framer-motion)
    // The drawer renders a dialog with aria-label
    expect(screen.getByRole('dialog', { name: 'Primary mobile navigation' })).toBeInTheDocument();
  });

  it('closes mobile menu on nav click', () => {
    const { container } = render(
      <Layout>
        <div>Test</div>
      </Layout>
    );
    const mobileBtn = container.querySelector('.md\\:hidden button') as HTMLButtonElement;
    fireEvent.click(mobileBtn);
    // Drawer should be open
    expect(screen.getByRole('dialog', { name: 'Primary mobile navigation' })).toBeInTheDocument();
    // Click the close button inside the drawer
    const closeBtn = screen.getByLabelText('Close menu');
    fireEvent.click(closeBtn);
    // Mobile drawer should be hidden
    expect(
      screen.queryByRole('dialog', { name: 'Primary mobile navigation' })
    ).not.toBeInTheDocument();
  });

  it('renders children in main content area', () => {
    render(
      <Layout>
        <div data-testid="child">Hello</div>
      </Layout>
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });
});
