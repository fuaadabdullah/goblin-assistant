import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('next/router', () => ({
  useRouter: () => ({
    asPath: '/unknown-page',
    push: jest.fn(),
    pathname: '/404',
    isReady: true,
    query: {},
    events: { on: jest.fn(), off: jest.fn() },
  }),
}));

jest.mock('next/link', () => {
  return function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
    return <a href={href}>{children}</a>;
  };
});

import NotFoundPage from '../NotFoundPage';

describe('NotFoundPage', () => {
  it('renders "Page not found" heading', () => {
    render(<NotFoundPage />);
    expect(screen.getByRole('heading', { name: /page not found/i })).toBeInTheDocument();
  });

  it('shows the current path', () => {
    render(<NotFoundPage />);
    expect(screen.getByText('/unknown-page')).toBeInTheDocument();
  });

  it('has a link back to home', () => {
    render(<NotFoundPage />);
    const link = screen.getByText('Back to Home');
    expect(link.closest('a')).toHaveAttribute('href', '/');
  });

  it('has a link to chat', () => {
    render(<NotFoundPage />);
    const link = screen.getByText('Go to Chat');
    expect(link.closest('a')).toHaveAttribute('href', '/chat');
  });

  it('renders the emoji', () => {
    render(<NotFoundPage />);
    expect(screen.getByText('🧭')).toBeInTheDocument();
  });
});
