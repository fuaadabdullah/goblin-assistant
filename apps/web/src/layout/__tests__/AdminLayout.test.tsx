import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

const mockReplace = jest.fn();
const mockUseRouter = jest.fn();
const mockUseAuthSession = jest.fn();
const mockNavigation = jest.fn();
const mockSeo = jest.fn();

jest.mock('next/router', () => ({
  useRouter: () => mockUseRouter(),
}));

jest.mock('../../hooks/api/useAuthSession', () => ({
  useAuthSession: () => mockUseAuthSession(),
}));

jest.mock('../../components/Navigation', () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    mockNavigation(props);
    return (
      <div
        data-testid="navigation"
        data-variant={String(props.variant)}
        data-show-logout={String(props.showLogout)}
      />
    );
  },
}));

jest.mock('../../components/Seo', () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    mockSeo(props);
    return <div data-testid="seo" data-title={String(props.title)} />;
  },
}));

import AdminLayout from '../AdminLayout';

describe('AdminLayout', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseRouter.mockReturnValue({
      asPath: '/admin/logs?tab=stream',
      replace: mockReplace,
    });
    mockUseAuthSession.mockReturnValue({
      isAuthenticated: true,
      isHydrated: true,
      hasRole: (role: string) => role === 'admin',
    });
  });

  it('returns null while auth state is not hydrated', () => {
    mockUseAuthSession.mockReturnValue({
      isAuthenticated: false,
      isHydrated: false,
      hasRole: () => false,
    });

    const { container } = render(
      <AdminLayout>
        <div>child</div>
      </AdminLayout>
    );

    expect(container.firstChild).toBeNull();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it('redirects unauthenticated users to login with encoded redirect', async () => {
    mockUseAuthSession.mockReturnValue({
      isAuthenticated: false,
      isHydrated: true,
      hasRole: () => false,
    });

    const { container } = render(
      <AdminLayout>
        <div>hidden</div>
      </AdminLayout>
    );

    expect(container.firstChild).toBeNull();
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/login?redirect=%2Fadmin%2Flogs%3Ftab%3Dstream');
    });
  });

  it('redirects authenticated non-admin users', async () => {
    mockUseAuthSession.mockReturnValue({
      isAuthenticated: true,
      isHydrated: true,
      hasRole: () => false,
    });

    render(
      <AdminLayout>
        <div>hidden</div>
      </AdminLayout>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/login?redirect=%2Fadmin%2Flogs%3Ftab%3Dstream');
    });
  });

  it('renders admin layout shell and main landmark for authorized admins', () => {
    render(
      <AdminLayout mainId="main-content" mainLabel="Admin Dashboard">
        <div>admin content</div>
      </AdminLayout>
    );

    expect(screen.getByTestId('seo')).toHaveAttribute('data-title', 'Admin');
    expect(screen.getByTestId('navigation')).toHaveAttribute('data-variant', 'admin');
    expect(screen.getByTestId('navigation')).toHaveAttribute('data-show-logout', 'true');
    expect(screen.getByRole('main', { name: 'Admin Dashboard' })).toBeInTheDocument();
    expect(screen.getByText('admin content')).toBeInTheDocument();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it('uses full-width content branch when mainId is not provided', () => {
    render(
      <AdminLayout fullWidth>
        <div data-testid="full-width-child">content</div>
      </AdminLayout>
    );

    const child = screen.getByTestId('full-width-child');
    expect(child.parentElement).toHaveClass('px-6');
  });
});
