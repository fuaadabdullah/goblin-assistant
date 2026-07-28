---
title: "STATE MANAGEMENT GUIDELINES"
description: "Frontend State Management Guidelines"
---

# Frontend State Management Guidelines

## Overview

GoblinOS Assistant uses a hybrid state management approach combining **React Query** for server state and **Zustand** for client state. This document outlines the patterns and best practices for maintaining clear separation of concerns.

## State Management Philosophy

- **Server State (React Query)**: Data that comes from the backend, requires synchronization, and may become stale
- **Client State (Zustand)**: UI state, user preferences, authentication status, and other client-side concerns

## React Query (Server State)

### When to Use

- API calls and data fetching
- Server-synchronized data that may become stale
- Operations that need caching, background refetching, or optimistic updates
- Data that multiple components need to share

### Patterns

#### 1. Pure Server State Hooks

```typescript
// ✅ GOOD: Pure server state management
export const useChatModels = () => {
  return useQuery({
    queryKey: queryKeys.models,
    queryFn: () => apiClient.getAvailableModels(),
  });
};
```

#### 2. Mutations Return Data to Components

```typescript
// ✅ GOOD: Components handle state updates
export const useLogin = () => {
  return useMutation({
    mutationFn: ({ email, password }: LoginParams) => apiClient.login(email, password),
    // No onSuccess callbacks that manipulate client state
  });
};

// In component:
const loginMutation = useLogin();
const handleLogin = async credentials => {
  try {
    const result = await loginMutation.mutateAsync(credentials);
    authStore.setAuth(result.user); // Component handles state update
  } catch (error) {
    // Handle error
  }
};
```

#### 3. Query Key Organization

```typescript
// ✅ GOOD: Hierarchical, typed query keys
export const queryKeys = {
  health: ['health'] as const,
  chat: {
    models: ['chat', 'models'] as const,
    routingInfo: ['chat', 'routing-info'] as const,
  },
  settings: {
    providers: ['settings', 'providers'] as const,
  },
} as const;
```

### Anti-Patterns

#### ❌ Direct State Manipulation in Hooks

```typescript
// ❌ BAD: Tight coupling between server and client state
export const useLogin = () => {
  const setAuth = useAuthStore(state => state.setAuth);

  return useMutation({
    mutationFn: loginApiCall,
    onSuccess: data => {
      setAuth(data.user); // Hook manipulates client state
    },
  });
};
```

## Zustand (Client State)

### When to Use

- Authentication state
- UI state (modals, drawers, active tabs)
- User preferences
- Form state that doesn't need to persist to server
- Global application state

### Patterns

#### 1. Single Responsibility Stores

```typescript
// ✅ GOOD: Focused, single-responsibility store
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  setAuth: (user: User) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>(set => ({
  user: null,
  isAuthenticated: false,
  setAuth: user => set({ user, isAuthenticated: true }),
  clearAuth: () => set({ user: null, isAuthenticated: false }),
}));
```

#### 2. Store Composition

```typescript
// ✅ GOOD: Compose related state
interface UIState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  activeModal: string | null;
}

export const useUIStore = create<UIState>(set => ({
  theme: 'light',
  sidebarOpen: true,
  activeModal: null,
  // ... actions
}));
```

### Anti-Patterns

#### ❌ Overly Broad Stores

```typescript
// ❌ BAD: Kitchen sink store
interface AppState {
  user: User | null;
  chatMessages: Message[];
  settings: Settings;
  uiTheme: string;
  isLoading: boolean;
  // ... many more
}
```

## Component Integration Patterns

### Pattern 1: Server State with Client State Updates

```typescript

// Component handles both server call and client state update
const LoginForm = () => {
  const loginMutation = useLogin();
  const setAuth = useAuthStore((state) => state.setAuth);

  const handleSubmit = async (credentials) => {
    try {
      const result = await loginMutation.mutateAsync(credentials);
      setAuth(result.user);
      navigate('/dashboard');
    } catch (error) {
      showError(error.message);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields */}
      <button disabled={loginMutation.isPending}>
        {loginMutation.isPending ? 'Logging in...' : 'Login'}
      </button>
    </form>
  );
};
```

### Pattern 2: Pure Server State Display

```typescript
// Component only displays server state
const ChatModelsList = () => {
  const { data: models, isLoading, error } = useChatModels();

  if (isLoading) return <div>Loading models...</div>;
  if (error) return <div>Error loading models</div>;

  return (
    <ul>
      {models?.map((model) => (
        <li key={model.id}>{model.name}</li>
      ))}
    </ul>
  );
};
```

### Pattern 3: Client State with Server Sync

```typescript

// Client state that syncs to server when needed
const ThemeToggle = () => {
  const { theme, setTheme } = useUIStore();
  const updateThemeMutation = useUpdateUserTheme();

  const handleThemeChange = async (newTheme) => {
    setTheme(newTheme); // Immediate UI update

    try {
      await updateThemeMutation.mutateAsync({ theme: newTheme });
    } catch (error) {
      // Revert on failure
      setTheme(theme);
      showError('Failed to save theme preference');
    }
  };

  return (
    <button onClick={() => handleThemeChange(theme === 'light' ? 'dark' : 'light')}>
      Toggle Theme
    </button>
  );
};
```

## Error Handling

### Server State Errors

```typescript
const { data, error, isError } = useQuery({
  queryKey: ['data'],
  queryFn: fetchData,
});

if (isError) {
  return <ErrorMessage error={error} />;
}
```

### Client State Errors

```typescript
const updateData = useStore(state => state.updateData);

const handleUpdate = async () => {
  try {
    await updateData(newData);
  } catch (error) {
    // Handle client state update errors
    console.error('Failed to update client state:', error);
  }
};
```

## Testing Patterns

### Testing Server State Hooks

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

test('useChatModels fetches models', async () => {
  const { result } = renderHook(() => useChatModels(), {
    wrapper: createWrapper(),
  });

  await waitFor(() => {
    expect(result.current.isSuccess).toBe(true);
  });

  expect(result.current.data).toBeDefined();
});
```

### Testing Client State

```typescript
import { renderHook, act } from '@testing-library/react';

test('useAuthStore manages auth state', () => {
  const { result } = renderHook(() => useAuthStore());

  act(() => {
    result.current.setAuth({ email: 'test@example.com' });
  });

  expect(result.current.isAuthenticated).toBe(true);
  expect(result.current.user?.email).toBe('test@example.com');
});
```

## Migration Guide

### From Coupled Hooks

1. Remove `onSuccess` callbacks that manipulate client state
2. Update components to handle state updates
3. Add proper error handling in components
4. Test the integration thoroughly

### Adding New State

1. Determine if it's server state (→ React Query) or client state (→ Zustand)
2. Follow the established patterns
3. Update this document if new patterns emerge

## Current State Assessment

### ✅ Strengths

- Clear separation between server and client state
- Well-organized query keys
- Proper error handling patterns
- Good TypeScript support

### 🔄 Areas for Improvement

- Some components still directly call `apiClient` instead of using hooks
- Could benefit from more client state stores for UI concerns
- Error boundaries could be enhanced for better UX

### 📊 Coverage

- **Server State**: Well covered with React Query hooks
- **Client State**: Basic auth store, room for expansion
- **Integration**: Components handle both appropriately
