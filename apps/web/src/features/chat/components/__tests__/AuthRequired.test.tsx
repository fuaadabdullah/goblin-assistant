import React from 'react';
import { render, screen } from '@testing-library/react';

vi.mock('next/link', () => ({
  default: function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
    return <a href={href}>{children}</a>;
  },
}));

import { AuthRequired } from '../AuthRequired';

describe('AuthRequired', () => {
  it('renders alert role', () => {
    render(<AuthRequired />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('shows sign in required heading', () => {
    render(<AuthRequired />);
    expect(screen.getByText('Sign in required')).toBeInTheDocument();
  });

  it('shows descriptive text', () => {
    render(<AuthRequired />);
    expect(screen.getByText(/need to be signed in/)).toBeInTheDocument();
  });

  it('renders sign in link to /login', () => {
    render(<AuthRequired />);
    const link = screen.getByText('Sign In');
    expect(link).toBeInTheDocument();
    expect(link.closest('a')).toHaveAttribute('href', '/login');
  });

  it('renders create account link to /login?mode=register', () => {
    render(<AuthRequired />);
    const link = screen.getByText('Create Account');
    expect(link).toBeInTheDocument();
    expect(link.closest('a')).toHaveAttribute('href', '/login?mode=register');
  });

  it('applies custom className', () => {
    render(<AuthRequired className="my-custom-class" />);
    expect(screen.getByRole('alert')).toHaveClass('my-custom-class');
  });

  it('defaults to empty className', () => {
    const { container } = render(<AuthRequired />);
    const alert = container.firstChild as HTMLElement;
    expect(alert.className).toContain('border');
  });
});
