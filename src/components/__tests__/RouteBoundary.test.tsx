import { describe, it, expect, beforeEach, afterAll, jest } from '@jest/globals';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import {
  RouteBoundaryFallback,
  withRouteErrorBoundary,
} from '../RouteBoundary';

jest.mock('next/router', () => ({
  useRouter: () => ({
    asPath: '/admin',
    replace: jest.fn().mockResolvedValue(true),
    prefetch: jest.fn().mockResolvedValue(undefined),
  }),
}));

jest.mock('../../hooks/api/useAuthSession', () => ({
  useAuthSession: () => ({
    isAuthenticated: true,
    isHydrated: true,
    hasRole: (role: string) => role === 'admin',
  }),
}));

jest.mock('../../components/Navigation', () => () => <nav data-testid="admin-navigation" />);
jest.mock('../../components/Seo', () => () => null);

const AdminLayout = require('../../layout/AdminLayout').default;

describe('RouteBoundaryFallback', () => {
  const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

  beforeEach(() => {
    jest.clearAllMocks();
    Object.defineProperty(global.navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: jest.fn().mockResolvedValue(undefined),
      },
    });
  });

  it('renders route-specific copy and actions', () => {
    render(
      <RouteBoundaryFallback
        title="Chat is temporarily unavailable"
        description="The conversation workspace crashed before it finished rendering."
        actions={[
          { type: 'link', label: 'Go Home', href: '/', variant: 'primary' },
          { type: 'link', label: 'Open Help', href: '/help', variant: 'secondary' },
        ]}
        technicalDetail="chat failure"
      />
    );

    expect(screen.getByText('Chat is temporarily unavailable')).toBeInTheDocument();
    expect(
      screen.getByText('The conversation workspace crashed before it finished rendering.')
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Go Home' })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: 'Open Help' })).toHaveAttribute('href', '/help');
  });

  it('renders the copy-error-id action only when an event ID exists', () => {
    const actions = [{ type: 'copyErrorId', label: 'Copy Error ID', variant: 'secondary' }];
    const { rerender } = render(
      <RouteBoundaryFallback
        title="Search is temporarily unavailable"
        description="The search experience failed before results could be shown."
        actions={[...actions]}
      />
    );

    expect(screen.queryByRole('button', { name: 'Copy Error ID' })).not.toBeInTheDocument();

    rerender(
      <RouteBoundaryFallback
        title="Search is temporarily unavailable"
        description="The search experience failed before results could be shown."
        actions={[...actions]}
        errorId="evt-456"
      />
    );

    expect(screen.getByRole('button', { name: 'Copy Error ID' })).toBeInTheDocument();
  });

  it('copies the exact event ID to the clipboard', async () => {
    render(
      <RouteBoundaryFallback
        title="Admin dashboard is unavailable"
        description="The dashboard view crashed before admin telemetry could load."
        actions={[{ type: 'copyErrorId', label: 'Copy Error ID', variant: 'secondary' }]}
        errorId="evt-copy"
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Copy Error ID' }));

    await waitFor(() => {
      expect((global.navigator.clipboard.writeText as jest.Mock)).toHaveBeenCalledWith('evt-copy');
    });

    expect(screen.getByRole('button', { name: 'Copied Error ID' })).toBeInTheDocument();
  });

  it('shows the chat-specific fallback when a wrapped chat component throws', () => {
    const WrappedChat = withRouteErrorBoundary(
      () => {
        throw new Error('chat boom');
      },
      'chat'
    );

    render(<WrappedChat />);

    expect(screen.getByText('Chat is temporarily unavailable')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open Help' })).toHaveAttribute('href', '/help');
  });

  it('renders admin fallback inside AdminLayout so navigation remains available', () => {
    const WrappedAdminContent = withRouteErrorBoundary(
      () => {
        throw new Error('admin boom');
      },
      'adminIndex'
    );

    render(
      <AdminLayout mainId="main-content" mainLabel="Admin Dashboard">
        <WrappedAdminContent />
      </AdminLayout>
    );

    expect(screen.getByTestId('admin-navigation')).toBeInTheDocument();
    expect(screen.getByText('Admin dashboard is unavailable')).toBeInTheDocument();
  });

  afterAll(() => {
    consoleErrorSpy.mockRestore();
  });
});
