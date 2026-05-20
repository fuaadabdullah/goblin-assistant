import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockPush = jest.fn();
let mockQuery: Record<string, string | undefined> = {};
let mockIsReady = true;

jest.mock('next/router', () => ({
  useRouter: () => ({
    isReady: mockIsReady,
    query: mockQuery,
    push: mockPush,
  }),
}));

jest.mock('@/utils/auth-session', () => ({
  persistAuthSession: jest.fn(),
}));

jest.mock('@/config/backendOrigin', () => ({
  resolvePublicBackendOrigin: () => 'http://localhost:8000',
}));

jest.mock('@/utils/dev-log', () => ({ devError: jest.fn() }));

import GoogleCallback from '../GoogleCallback';
import { persistAuthSession } from '@/utils/auth-session';

function renderWithClient(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('GoogleCallback', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockQuery = {};
    mockIsReady = true;
    global.fetch = jest.fn();
  });

  afterEach(() => {
    delete (global as unknown as Record<string, unknown>).fetch;
  });

  it('renders loading state', () => {
    mockIsReady = false;
    renderWithClient(<GoogleCallback />);
    expect(screen.getByText('Completing sign in...')).toBeInTheDocument();
  });

  it('redirects on OAuth error param', async () => {
    mockQuery = { error: 'access_denied' };
    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=oauth_failed'));
  });

  it('redirects when no code received', async () => {
    mockQuery = {};
    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=no_code'));
  });

  it('exchanges code for token on success', async () => {
    mockQuery = { code: 'abc123', state: 'xyz' };
    const mockFetch = global.fetch as jest.Mock;
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        token: 'jwt-token',
        user: { id: 1, name: 'Test' },
        refresh_token: 'refresh-123',
        expires_in: 3600,
      }),
    });

    renderWithClient(<GoogleCallback />);
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/auth/google/callback',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ code: 'abc123', state: 'xyz' }),
        }),
      );
    });
    await waitFor(() => {
      expect(persistAuthSession).toHaveBeenCalledWith(expect.objectContaining({
        token: 'jwt-token',
        user: { id: 1, name: 'Test' },
      }));
    });
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/chat'));
  });

  it('redirects to login on fetch error', async () => {
    mockQuery = { code: 'abc123' };
    const mockFetch = global.fetch as jest.Mock;
    mockFetch.mockResolvedValue({
      ok: false,
      statusText: 'Bad Request',
      json: () => Promise.resolve({ detail: 'Invalid code' }),
    });

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=callback_failed'));
  });

  it('redirects on invalid response (no token)', async () => {
    mockQuery = { code: 'abc123' };
    const mockFetch = global.fetch as jest.Mock;
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ token: null, user: null }),
    });

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=callback_failed'));
  });

  it('redirects on network error', async () => {
    mockQuery = { code: 'abc123' };
    const mockFetch = global.fetch as jest.Mock;
    mockFetch.mockRejectedValue(new Error('network down'));

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=callback_failed'));
  });

  it('does nothing when router not ready', () => {
    mockIsReady = false;
    mockQuery = { code: 'abc123' };
    renderWithClient(<GoogleCallback />);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('renders spinne  placeholder text', () => {
    renderWithClient(<GoogleCallback />);
    expect(screen.getByText(/Please wait/)).toBeInTheDocument();
  });
});
