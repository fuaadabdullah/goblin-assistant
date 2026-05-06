import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import AccountPage from '../AccountPage';

jest.mock('@/features/account/AccountScreen', () => function MockAccountScreen() {
  return <div data-testid="account-screen">Account Screen</div>;
});

describe('AccountPage', () => {
  it('renders AccountScreen component', () => {
    render(<AccountPage />);
    expect(screen.getByTestId('account-screen')).toBeInTheDocument();
  });

  it('displays account content', () => {
    render(<AccountPage />);
    expect(screen.getByText('Account Screen')).toBeInTheDocument();
  });

  it('has proper page structure', () => {
    const { container } = render(<AccountPage />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
