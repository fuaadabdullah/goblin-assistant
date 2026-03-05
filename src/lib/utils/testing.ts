// Testing utilities for Goblin Assistant

// Mock utilities
export class MockUtils {
  // Mock localStorage
  static mockLocalStorage(): any {
    const store: Record<string, string> = {};
    
    return {
      getItem: (key: string) => store[key] || null,
      setItem: (key: string, value: string) => {
        store[key] = value;
      },
      removeItem: (key: string) => {
        delete store[key];
      },
      clear: () => {
        Object.keys(store).forEach(key => delete store[key]);
      },
      get length() {
        return Object.keys(store).length;
      },
      key: (index: number) => Object.keys(store)[index] || null,
    };
  }

  // Mock API responses
  static mockApiResponse<T>(data: T, delay = 0): Promise<T> {
    return new Promise((resolve) => {
      setTimeout(() => resolve(data), delay);
    });
  }

  // Mock API error
  static mockApiError(message = 'Mock API error', status = 500): Promise<never> {
    return new Promise((_, reject) => {
      setTimeout(() => {
        const error = new Error(message) as any;
        error.response = { status };
        reject(error);
      }, 100);
    });
  }
}

// Test helpers
export class TestHelpers {
  // Wait for next tick
  static async nextTick(): Promise<void> {
    return new Promise(resolve => process.nextTick(resolve));
  }

  // Wait for microtasks
  static async waitForMicrotasks(): Promise<void> {
    await new Promise(resolve => setTimeout(resolve, 0));
  }

  // Create a test user
  static createTestUser(overrides: Partial<any> = {}): any {
    return {
      id: 'test-user-123',
      email: 'test@example.com',
      name: 'Test User',
      role: 'user',
      createdAt: new Date().toISOString(),
      ...overrides,
    };
  }

  // Create test chat session
  static createTestSession(overrides: Partial<any> = {}): any {
    return {
      id: 'test-session-123',
      title: 'Test Session',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      model: 'gpt-4',
      totalCost: 0,
      totalTokens: 0,
      ...overrides,
    };
  }

  // Create test message
  static createTestMessage(overrides: Partial<any> = {}): any {
    return {
      id: 'test-message-123',
      content: 'Test message content',
      role: 'user' as const,
      timestamp: new Date().toISOString(),
      model: 'gpt-4',
      cost: 0.01,
      tokens: {
        prompt: 10,
        completion: 20,
        total: 30,
      },
      ...overrides,
    };
  }

  // Wait for condition
  static async waitFor<T>(
    callback: () => T | undefined,
    options: { timeout?: number; interval?: number } = {}
  ): Promise<T> {
    const { timeout = 5000, interval = 50 } = options;
    const start = Date.now();
    
    while (Date.now() - start < timeout) {
      const result = callback();
      if (result !== undefined) {
        return result;
      }
      await new Promise(resolve => setTimeout(resolve, interval));
    }
    
    throw new Error(`waitFor timeout after ${timeout}ms`);
  }

  // Flush promises
  static async flushPromises(): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, 0));
  }
}

// Accessibility testing utilities
export class A11yHelpers {
  // Check if element is focusable
  static isFocusable(element: HTMLElement): boolean {
    if (element.tabIndex > 0) return true;
    if (element.tabIndex === 0 && !element.hasAttribute('disabled')) return true;
    
    const focusableTags = ['a', 'button', 'input', 'select', 'textarea', 'details'];
    if (focusableTags.includes(element.tagName.toLowerCase())) {
      return !element.hasAttribute('disabled');
    }
    
    return element.hasAttribute('contenteditable') ||
           element.getAttribute('tabindex') === '0';
  }

  // Get all focusable elements in container
  static getFocusableElements(container: HTMLElement): HTMLElement[] {
    const focusableSelector = [
      'a[href]',
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      'details',
      '[contenteditable="true"]',
      '[tabindex]:not([tabindex="-1"])',
    ].join(', ');
    
    return Array.from(container.querySelectorAll<HTMLElement>(focusableSelector))
      .filter(element => {
        const style = window.getComputedStyle(element);
        return style.display !== 'none' && style.visibility !== 'hidden';
      });
  }
}

// Performance testing utilities
export class PerformanceHelpers {
  // Check memory usage
  static getMemoryUsage(): any {
    if ('memory' in performance) {
      return (performance as any).memory;
    }
    return null;
  }
}

// Mock data factories
export class MockFactories {
  // Create mock API client
  static createMockApiClient(): any {
    return {
      get: () => {},
      post: () => {},
      put: () => {},
      patch: () => {},
      delete: () => {},
      upload: () => {},
      setAuthToken: () => {},
      getAuthToken: () => {},
      clearAuth: () => {},
    };
  }

  // Create mock store
  static createMockStore(): any {
    return {
      useAuthStore: {
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
        login: () => {},
        register: () => {},
        logout: () => {},
        refreshAuth: () => {},
        clearError: () => {},
      },
      useChatStore: {
        sessions: [],
        currentSessionId: null,
        isLoading: false,
        error: null,
        createSession: () => {},
        setCurrentSession: () => {},
        addMessage: () => {},
        updateMessage: () => {},
        deleteSession: () => {},
        clearSession: () => {},
        loadHistory: () => {},
        sendMessage: () => {},
        streamMessage: () => {},
        clearError: () => {},
      },
      useSettingsStore: {
        preferences: {
          theme: 'default',
          highContrast: false,
          fontSize: 'md',
          language: 'en',
          notifications: true,
          autoSave: true,
          compactMode: false,
        },
        providerSettings: {
          openai: {
            apiKey: '',
            model: 'gpt-4',
            temperature: 0.7,
            maxTokens: 4000,
          },
          anthropic: {
            apiKey: '',
            model: 'claude-3-sonnet-20240229',
            temperature: 0.7,
            maxTokens: 4000,
          },
          google: {
            apiKey: '',
            model: 'gemini-pro',
            temperature: 0.7,
            maxTokens: 4000,
          },
        },
        isLoading: false,
        error: null,
        updatePreferences: () => {},
        updateProviderSettings: () => {},
        loadSettings: () => {},
        resetSettings: () => {},
        clearError: () => {},
      },
    };
  }

}

// Test configuration
export const testConfig = {
  // Default timeouts
  timeouts: {
    render: 100,
    api: 1000,
    animation: 300,
  },
  
  // Mock data
  mocks: {
    user: TestHelpers.createTestUser(),
    session: TestHelpers.createTestSession(),
    message: TestHelpers.createTestMessage(),
  },
};
