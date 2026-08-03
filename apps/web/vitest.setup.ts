import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach } from 'vitest';
import { cleanup } from '@testing-library/react';

function storageKeys(storage: Storage) {
  return Object.keys(storage).filter((key) => typeof storage[key as keyof Storage] !== 'function');
}

function installStoragePrototype() {
  Object.defineProperties(Storage.prototype, {
    clear: {
      configurable: true,
      writable: true,
      value() {
        for (const key of storageKeys(this)) {
          delete this[key as keyof Storage];
        }
      },
    },
    getItem: {
      configurable: true,
      writable: true,
      value(key: string) {
        return Object.prototype.hasOwnProperty.call(this, key)
          ? String(this[key as keyof Storage])
          : null;
      },
    },
    key: {
      configurable: true,
      writable: true,
      value(index: number) {
        return storageKeys(this)[index] ?? null;
      },
    },
    removeItem: {
      configurable: true,
      writable: true,
      value(key: string) {
        delete this[key as keyof Storage];
      },
    },
    setItem: {
      configurable: true,
      writable: true,
      value(key: string, value: string) {
        Object.defineProperty(this, key, {
          configurable: true,
          enumerable: true,
          writable: true,
          value: String(value),
        });
      },
    },
  });

  Object.defineProperty(Storage.prototype, 'length', {
    configurable: true,
    get() {
      return storageKeys(this).length;
    },
  });
}

function createStorage() {
  return Object.create(Storage.prototype) as Storage;
}

function installStorageProperty(property: 'localStorage' | 'sessionStorage') {
  const storage = createStorage();
  Object.defineProperty(window, property, {
    configurable: true,
    writable: true,
    value: storage,
  });
  Object.defineProperty(globalThis, property, {
    configurable: true,
    writable: true,
    value: storage,
  });
}

beforeEach(() => {
  installStoragePrototype();
  installStorageProperty('localStorage');
  installStorageProperty('sessionStorage');
});

afterEach(() => {
  cleanup();
});

// @ts-expect-error — React Testing Library needs this flag
global.IS_REACT_ACT_ENVIRONMENT = true;

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
