// Global type declarations for mixed server/client environments

declare global {
  // WebSocket types for browser vs Node.js
  var WebSocket: typeof globalThis.WebSocket;
  var TextDecoder: typeof globalThis.TextDecoder;
  var TextEncoder: typeof globalThis.TextEncoder;
  
  // Performance API with Node.js fallback
  var performance: {
    now(): number;
    mark(name: string): void;
    measure(name: string, startMark?: string, endMark?: string): void;
  };
  
  // Additional DOM globals that might be undefined in server context
  var IntersectionObserver: typeof globalThis.IntersectionObserver;
  var MutationObserver: typeof globalThis.MutationObserver;
  var Image: typeof globalThis.Image;
}

export {};