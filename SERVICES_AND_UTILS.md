# Goblin Assistant - Services and Utilities

This document describes the services and utilities built for the Goblin Assistant frontend.

## Overview

The services and utilities layer provides the foundation for API communication, state management, and common functionality across the application. It includes:

- **API Client**: Centralized HTTP client with interceptors and error handling
- **State Management**: Zustand stores for global state
- **Utilities**: Common functions for formatting, validation, and utilities

## 🌐 API Client (`src/lib/services/api-client.ts`)

A centralized HTTP client built on top of Axios with comprehensive error handling and authentication.

### Features
- **Automatic Authentication**: Token management with localStorage
- **Error Handling**: Global error handling with user feedback
- **Request/Response Interceptors**: Consistent request/response processing
- **File Upload**: Support for file uploads with progress tracking
- **Type Safety**: Full TypeScript support

### Usage
```typescript
import { apiClient, apiEndpoints } from 'src/lib/services/api-client';

// GET request
const users = await apiClient.get<User[]>(apiEndpoints.users.list);

// POST request
const newUser = await apiClient.post<User>(apiEndpoints.users.create, {
  name: 'John Doe',
  email: 'john@example.com'
});

// File upload
const uploadedFile = await apiClient.upload<File>(
  apiEndpoints.files.upload,
  file,
  (progress) => console.log(`Upload progress: ${progress}%`)
);
```

### API Endpoints
```typescript
export const apiEndpoints = {
  auth: {
    login: '/api/auth/login',
    register: '/api/auth/register',
    logout: '/api/auth/logout',
    me: '/api/auth/me',
  },
  chat: {
    messages: '/api/chat/messages',
    stream: '/api/chat/stream',
    history: '/api/chat/history',
  },
  providers: {
    list: '/api/providers',
    health: '/api/providers/health',
    settings: '/api/providers/settings',
  },
  analytics: {
    usage: '/api/analytics/usage',
    costs: '/api/analytics/costs',
    providers: '/api/analytics/providers',
  },
  settings: {
    user: '/api/settings/user',
    theme: '/api/settings/theme',
    preferences: '/api/settings/preferences',
    settings: '/api/settings/providers',
  },
};
```

## 🗄️ State Management (`src/lib/store/`)

Global state management using Zustand with persistence and TypeScript.

### Auth Store (`auth-store.ts`)
Manages user authentication state and actions.

**State:**
- `user`: Current user information
- `token`: Authentication token
- `isAuthenticated`: Authentication status
- `isLoading`: Loading state
- `error`: Error messages

**Actions:**
- `login(email, password)`: User login
- `register(name, email, password)`: User registration
- `logout()`: User logout
- `refreshAuth()`: Refresh authentication
- `setUser(user)`: Set user data
- `setToken(token)`: Set authentication token

```typescript
import { useAuthStore } from 'src/lib/store/auth-store';

const { user, isAuthenticated, login, logout } = useAuthStore();

// Login
await login('user@example.com', 'password123');

// Logout
logout();
```

### Chat Store (`chat-store.ts`)
Manages chat sessions, messages, and streaming.

**State:**
- `sessions`: Array of chat sessions
- `currentSessionId`: Active session ID
- `isLoading`: Loading state
- `error`: Error messages

**Actions:**
- `createSession(title)`: Create new chat session
- `setCurrentSession(sessionId)`: Switch active session
- `addMessage(message)`: Add message to current session
- `updateMessage(messageId, updates)`: Update message
- `deleteSession(sessionId)`: Delete chat session
- `sendMessage(content)`: Send message (non-streaming)
- `streamMessage(content)`: Send message (streaming)
- `loadHistory()`: Load chat history

```typescript
import { useChatStore } from 'src/lib/store/chat-store';

const { sessions, currentSessionId, sendMessage, streamMessage } = useChatStore();

// Send message
await sendMessage('Hello, how are you?');

// Stream message
await streamMessage('Please write a story about...');
```

### Settings Store (`settings-store.ts`)
Manages user preferences and provider settings.

**State:**
- `preferences`: User interface preferences
- `providerSettings`: AI provider configurations
- `isLoading`: Loading state
- `error`: Error messages

**Actions:**
- `updatePreferences(updates)`: Update user preferences
- `updateProviderSettings(provider, settings)`: Update provider settings
- `loadSettings()`: Load settings from server
- `resetSettings()`: Reset to default settings

```typescript
import { useSettingsStore } from 'src/lib/store/settings-store';

const { preferences, providerSettings, updatePreferences } = useSettingsStore();

// Update theme preference
await updatePreferences({ theme: 'nocturne', highContrast: true });
```

## 🔧 Utilities (`src/lib/utils/index.ts`)

Comprehensive utility functions for common operations.

### Formatting Utilities
```typescript
import { formatCurrency, formatNumber, formatBytes } from 'src/lib/utils';

formatCurrency(1234.56); // "$1,234.56"
formatNumber(1234567);   // "1,234,567"
formatBytes(1024 * 1024); // "1 MB"
```

### Date Utilities
```typescript
import { formatDate, formatDateTime, timeAgo } from 'src/lib/utils';

formatDate(new Date());     // "Dec 24, 2025"
formatDateTime(new Date()); // "Dec 24, 2025, 4:00 PM"
timeAgo('2025-12-24T15:30:00Z'); // "2 hours ago"
```

### String Utilities
```typescript
import { truncateString, capitalize, slugify } from 'src/lib/utils';

truncateString('Hello World', 5); // "Hello..."
capitalize('hello world');        // "Hello world"
slugify('Hello World!');          // "hello-world"
```

### Array Utilities
```typescript
import { chunkArray, uniqueArray, groupBy } from 'src/lib/utils';

chunkArray([1, 2, 3, 4, 5], 2); // [[1, 2], [3, 4], [5]]
uniqueArray([1, 2, 2, 3, 3]);    // [1, 2, 3]
groupBy(users, user => user.age); // { 25: [...], 30: [...] }
```

### Validation Utilities
```typescript
import { isValidEmail, isValidUrl, isValidApiKey } from 'src/lib/utils';

isValidEmail('user@example.com'); // true
isValidUrl('https://example.com'); // true
isValidApiKey('sk-1234567890');    // true
```

### Local Storage Utilities
```typescript
import { localStorageGet, localStorageSet, localStorageRemove } from 'src/lib/utils';

localStorageSet('theme', 'dark');
const theme = localStorageGet('theme', 'light'); // 'dark'
localStorageRemove('theme');
```

### Performance Utilities
```typescript
import { debounce, throttle, measureTime } from 'src/lib/utils';

// Debounce function calls
const debouncedSearch = debounce((query) => {
  // Search logic
}, 300);

// Throttle function calls
const throttledScroll = throttle(() => {
  // Scroll handler
}, 100);

// Measure execution time
const { result, time } = await measureTime(async () => {
  // Some async operation
  return 'result';
});
```

### Color Utilities
```typescript
import { hexToRgb, rgbToHex, lightenColor, darkenColor } from 'src/lib/utils';

hexToRgb('#ff0000');        // { r: 255, g: 0, b: 0 }
rgbToHex(255, 0, 0);        // "#ff0000"
lightenColor('#ff0000', 20); // Lighten by 20%
darkenColor('#ff0000', 20);  // Darken by 20%
```

### Type Guards
```typescript
import { isString, isNumber, isObject, isArray } from 'src/lib/utils';

isString('hello');  // true
isNumber(42);       // true
isObject({});      // true
isArray([1, 2, 3]); // true
```

## 🏗️ Architecture Patterns

### Service Layer Pattern
The services layer follows the service layer pattern, providing a clean abstraction between the UI and data layers.

```typescript
// Service layer
class UserService {
  async getUser(id: string): Promise<User> {
    return apiClient.get<User>(`${apiEndpoints.users.get}/${id}`);
  }
  
  async updateUser(id: string, data: Partial<User>): Promise<User> {
    return apiClient.put<User>(`${apiEndpoints.users.update}/${id}`, data);
  }
}

// Usage in components
const userService = new UserService();
const user = await userService.getUser('123');
```

### State Management Pattern
Zustand stores follow a consistent pattern:

1. **State Interface**: TypeScript interface defining the store state
2. **Actions**: Functions that modify the state
3. **Persistence**: Automatic persistence using `persist` middleware
4. **Error Handling**: Consistent error handling across actions

### Utility Organization
Utilities are organized by category:
- **Formatting**: Data formatting functions
- **Validation**: Input validation functions
- **Date/Time**: Date and time utilities
- **Performance**: Performance optimization utilities
- **Type Guards**: TypeScript type guard functions

## 🚀 Best Practices

### API Client Usage
1. **Use Constants**: Always use `apiEndpoints` constants
2. **Error Handling**: Handle errors appropriately in components
3. **Type Safety**: Always specify return types for API calls
4. **Authentication**: The client automatically handles authentication

### State Management
1. **Store Separation**: Separate stores by domain (auth, chat, settings)
2. **Action Patterns**: Follow consistent action patterns
3. **Persistence**: Use `persist` middleware for important state
4. **Error State**: Always include error state in stores

### Utilities
1. **Reusability**: Create utilities for common operations
2. **Type Safety**: Always provide TypeScript types
3. **Testing**: Write tests for utility functions
4. **Documentation**: Document complex utility functions

## 📊 Performance Considerations

### API Client
- **Request Caching**: Consider implementing caching for frequently accessed data
- **Error Handling**: Global error handling reduces boilerplate
- **Interceptors**: Centralized request/response processing

### State Management
- **Selective Updates**: Zustand only updates when state actually changes
- **Persistence**: Automatic persistence with minimal performance impact
- **Store Size**: Keep stores focused and avoid storing unnecessary data

### Utilities
- **Memoization**: Use memoization for expensive calculations
- **Debouncing**: Debounce user input to reduce API calls
- **Throttling**: Throttle scroll/resize events

## 🔧 Configuration

### API Client Configuration
```typescript
// Environment variables
NEXT_PUBLIC_API_URL=http://localhost:8000

// Client options
const client = new ApiClient({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 10000,
  withCredentials: true,
});
```

### Store Persistence
```typescript
// Configure persistence
persist(
  (set) => ({ /* store */ }),
  {
    name: 'store-name', // localStorage key
    partialize: (state) => ({
      // Only persist specific fields
      field1: state.field1,
      field2: state.field2,
    }),
  }
);
```

## 🧪 Testing

### API Client Testing
```typescript
// Mock API client for testing
jest.mock('src/lib/services/api-client');

// Test store actions
describe('AuthStore', () => {
  it('should login user', async () => {
    const { result } = renderHook(() => useAuthStore());
    
    await act(async () => {
      await result.current.login('user@example.com', 'password');
    });
    
    expect(result.current.isAuthenticated).toBe(true);
  });
});
```

### Utility Testing
```typescript
describe('formatCurrency', () => {
  it('should format currency correctly', () => {
    expect(formatCurrency(1234.56)).toBe('$1,234.56');
  });
});
```

## 📚 Next Steps

1. **Additional Stores**: Create stores for analytics, providers, etc.
2. **Advanced Caching**: Implement advanced caching strategies
3. **Performance Monitoring**: Add performance monitoring utilities
4. **Error Tracking**: Integrate with error tracking services
5. **Testing**: Expand test coverage for all utilities and stores

For more information, see the main [ORGANIZATION.md](./ORGANIZATION.md) file.
