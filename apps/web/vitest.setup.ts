import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
});

// @ts-expect-error — React Testing Library needs this flag
global.IS_REACT_ACT_ENVIRONMENT = true;

class MemoryStorage implements Storage {
  private readonly items = new Map<string, string>();

  get length() {
    return this.items.size;
  }

  clear() {
    this.items.clear();
  }

  getItem(key: string) {
    return this.items.get(key) ?? null;
  }

  key(index: number) {
    return Array.from(this.items.keys())[index] ?? null;
  }

  removeItem(key: string) {
    this.items.delete(key);
  }

  setItem(key: string, value: string) {
    this.items.set(key, String(value));
  }
}

const storageBuckets = new WeakMap<Storage, Map<string, string>>();
let storagePrototypeFallbackInstalled = false;

const getStorageBucket = (storage: Storage) => {
  let bucket = storageBuckets.get(storage);
  if (!bucket) {
    bucket = new Map<string, string>();
    storageBuckets.set(storage, bucket);
  }
  return bucket;
};

const storagePrototypeFallbackDescriptors: PropertyDescriptorMap = {
  length: {
    configurable: true,
    get(this: Storage) {
      return getStorageBucket(this).size;
    },
  },
  clear: {
    configurable: true,
    value(this: Storage) {
      getStorageBucket(this).clear();
    },
    writable: true,
  },
  getItem: {
    configurable: true,
    value(this: Storage, key: string) {
      return getStorageBucket(this).get(key) ?? null;
    },
    writable: true,
  },
  key: {
    configurable: true,
    value(this: Storage, index: number) {
      return Array.from(getStorageBucket(this).keys())[index] ?? null;
    },
    writable: true,
  },
  removeItem: {
    configurable: true,
    value(this: Storage, key: string) {
      getStorageBucket(this).delete(key);
    },
    writable: true,
  },
  setItem: {
    configurable: true,
    value(this: Storage, key: string, value: string) {
      getStorageBucket(this).set(key, String(value));
    },
    writable: true,
  },
};

const installStoragePrototypeFallback = () => {
  if (storagePrototypeFallbackInstalled || typeof Storage === 'undefined') return;

  storagePrototypeFallbackInstalled = true;
  Object.defineProperties(Storage.prototype, storagePrototypeFallbackDescriptors);
};

const createStorageFallback = () => {
  if (typeof Storage === 'undefined') {
    return new MemoryStorage();
  }

  installStoragePrototypeFallback();
  const storage = Object.create(Storage.prototype) as Storage;
  storageBuckets.set(storage, new Map<string, string>());
  return storage;
};

const installStorageFallback = (property: 'localStorage' | 'sessionStorage') => {
  if (window[property]) return;

  const storage = createStorageFallback();
  Object.defineProperty(window, property, {
    configurable: true,
    value: storage,
    writable: true,
  });
  Object.defineProperty(globalThis, property, {
    configurable: true,
    value: storage,
    writable: true,
  });
};

installStorageFallback('localStorage');
installStorageFallback('sessionStorage');

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
    dispatchEvent: () => false,
  }),
});

global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

global.IntersectionObserver = class IntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof IntersectionObserver;
