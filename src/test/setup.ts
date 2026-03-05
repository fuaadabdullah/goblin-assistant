import '@testing-library/jest-dom';
import { afterEach } from '@jest/globals';
import { cleanup } from '@testing-library/react';
import fetch, { Headers, Request, Response } from 'cross-fetch';

// Ensure tests don't accidentally hit real backends.
process.env.NEXT_PUBLIC_FASTAPI_URL ||= 'http://127.0.0.1:8000';
process.env.NEXT_PUBLIC_API_URL ||= 'http://127.0.0.1:8000';
process.env.NEXT_PUBLIC_API_BASE_URL ||= 'http://127.0.0.1:8000';

// Polyfill fetch for Jest (Node + JSDOM).
(globalThis as any).fetch ||= fetch;
(globalThis as any).Headers ||= Headers;
(globalThis as any).Request ||= Request;
(globalThis as any).Response ||= Response;

// Cleanup after each test case
afterEach(() => {
  cleanup();
});

// JSDOM-only shims
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => {},
    }),
  });
}

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor(cb: ResizeObserverCallback) {}
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  observe() {}
  unobserve() {}
  disconnect() {}
};
