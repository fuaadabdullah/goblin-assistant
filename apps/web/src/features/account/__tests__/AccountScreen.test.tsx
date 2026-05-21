import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

const mockUseAuthSession = jest.fn();
const mockUseAccountProfile = jest.fn();
const mockAccountView = jest.fn();

jest.mock('../../../hooks/api/useAuthSession', () => ({
  useAuthSession: () => mockUseAuthSession(),
}));

jest.mock('../hooks/useAccountProfile', () => ({
  useAccountProfile: (...args: unknown[]) => mockUseAccountProfile(...args),
}));

jest.mock('../components/AccountView', () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    mockAccountView(props);
    return <div data-testid="account-view" />;
  },
}));

import AccountScreen from '../AccountScreen';

describe('AccountScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthSession.mockReturnValue({ user: { name: 'Test', email: 'test@example.com' } });
    mockUseAccountProfile.mockReturnValue({
      name: 'Test',
      email: 'test@example.com',
      saved: false,
      error: null,
      saving: false,
      preferences: { summaries: true, notifications: true, familyMode: false },
      setName: jest.fn(),
      togglePreference: jest.fn(),
      handleSave: jest.fn(),
    });
  });

  it('passes authenticated user to useAccountProfile', () => {
    const user = { name: 'Alice', email: 'alice@example.com' };
    mockUseAuthSession.mockReturnValue({ user });

    render(<AccountScreen />);

    expect(mockUseAccountProfile).toHaveBeenCalledWith(user);
  });

  it('passes account state to AccountView', () => {
    const state = {
      name: 'Bob',
      email: 'bob@example.com',
      saved: true,
      error: null,
      saving: false,
      preferences: { summaries: true, notifications: false, familyMode: true },
      setName: jest.fn(),
      togglePreference: jest.fn(),
      handleSave: jest.fn(),
    };
    mockUseAccountProfile.mockReturnValue(state);

    render(<AccountScreen />);

    expect(screen.getByTestId('account-view')).toBeInTheDocument();
    expect(mockAccountView).toHaveBeenCalledWith(expect.objectContaining({ state }));
  });

  it('supports unauthenticated/empty user state', () => {
    mockUseAuthSession.mockReturnValue({ user: null });

    render(<AccountScreen />);

    expect(mockUseAccountProfile).toHaveBeenCalledWith(null);
    expect(screen.getByTestId('account-view')).toBeInTheDocument();
  });
});
