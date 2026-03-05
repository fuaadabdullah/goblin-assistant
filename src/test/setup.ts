import '@testing-library/jest-dom';
import { expect, afterEach, beforeAll, afterAll, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import { handlers } from './mswServer';
import type { SetupServerApi } from 'msw/node';

let mswServer: SetupServerApi | null = null;

// Initialize MSW server
async function initMswServer() {
  if (!mswServer) {
    const { setupServer } = await import('msw/node');
    mswServer = setupServer(...handlers);
  }
  return mswServer;
}

// Start MSW server before all tests
beforeAll(async () => {
  const server = await initMswServer();
  if (server) {
    server.listen({ onUnhandledRequest: 'error' });
  }
});

// Reset handlers after each test
afterEach(async () => {
  const server = await initMswServer();
  if (server) {
    server.resetHandlers();
  }
  cleanup();
});

// Stop server after all tests
afterAll(async () => {
  const server = await initMswServer();
  if (server) {
    server.close();
  }
});

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: vi.fn(),
      replace: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
      prefetch: vi.fn(),
      pathname: '/',
      query: {},
      asPath: '/',
    };
  },
  useSearchParams() {
    return new URLSearchParams();
  },
  usePathname() {
    return '/';
  },
}));

// Mock next/router (for pages directory)
vi.mock('next/router', () => ({
  useRouter() {
    return {
      push: vi.fn(),
      replace: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      reload: vi.fn(),
      pathname: '/',
      query: {},
      asPath: '/',
      route: '/',
    };
  },
}));

// Mock Supabase
vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getUser: vi.fn(),
      signInWithPassword: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      resetPasswordForEmail: vi.fn(),
      onAuthStateChange: vi.fn(),
    },
    from: vi.fn(() => ({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue(Promise.resolve({ data: [], error: null })),
        single: vi.fn().mockReturnValue(Promise.resolve({ data: null, error: null })),
      }),
      insert: vi.fn().mockReturnValue(Promise.resolve({ data: [], error: null })),
      update: vi.fn().mockReturnValue(Promise.resolve({ data: [], error: null })),
      delete: vi.fn().mockReturnValue(Promise.resolve({ data: [], error: null })),
    })),
  })),
}));

// Mock environment variables
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8001';
process.env.NEXT_PUBLIC_SUPABASE_URL = 'https://test.supabase.co';
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-key';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

