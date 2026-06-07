import React from 'react';
import { render, screen } from '@testing-library/react';
import AccountPage from '../AccountPage';

vi.mock(
  '@/features/account/AccountScreen',
  () => ({
    default: function MockAccountScreen() {
      return <div data-testid="account-screen">Account Screen</div>;
    },
  })
);

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
