import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('lucide-react', () => new Proxy({}, {
  get: (_, name) => {
    if (name === '__esModule') return true;
    return (props: Record<string, unknown>) => <span data-testid={`icon-${String(name)}`} {...props} />;
  },
}));

jest.mock('../../../content/brand', () => ({
  BRAND_NAME: 'TestGoblin',
}));

import LoginHeader from '../LoginHeader';

describe('LoginHeader', () => {
  it('renders the brand name', () => {
    render(<LoginHeader isRegister={false} />);
    expect(screen.getByText('TestGoblin')).toBeInTheDocument();
  });

  it('shows Welcome Back for login', () => {
    render(<LoginHeader isRegister={false} />);
    expect(screen.getByText('Welcome Back')).toBeInTheDocument();
  });

  it('shows Create Account for register', () => {
    render(<LoginHeader isRegister={true} />);
    expect(screen.getByText('Create Account')).toBeInTheDocument();
  });

  it('shows sign-in description for login', () => {
    render(<LoginHeader isRegister={false} />);
    expect(screen.getByText(/Sign in to access/)).toBeInTheDocument();
  });

  it('shows create-account description for register', () => {
    render(<LoginHeader isRegister={true} />);
    expect(screen.getByText(/Create an account/)).toBeInTheDocument();
  });

  it('renders the Bot icon', () => {
    render(<LoginHeader isRegister={false} />);
    expect(screen.getByTestId('icon-Bot')).toBeInTheDocument();
  });
});
