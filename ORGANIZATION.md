# Goblin Assistant - Project Organization

This document outlines the organized structure of the Goblin Assistant frontend project.

## Directory Structure

```
apps/goblin-assistant/
├── src/                          # Main source code directory
│   ├── components/               # All React components
│   │   ├── ui/                  # Reusable UI components (Radix-based)
│   │   ├── layout/              # Layout components
│   │   ├── chat/                # Chat-specific components
│   │   ├── dashboard/           # Dashboard-specific components
│   │   ├── admin/               # Admin-specific components
│   │   ├── auth/                # Authentication components
│   │   ├── common/              # Shared business components
│   │   ├── ErrorBoundary.tsx    # Error boundary component
│   │   └── ErrorFallback.tsx    # Error fallback component
│   ├── hooks/                   # Custom React hooks
│   │   ├── useApi.ts           # API hook
│   │   ├── useChat.ts          # Chat hook
│   │   ├── useDebounce.ts      # Debounce hook
│   │   ├── useLocalStorage.ts  # Local storage hook
│   │   ├── useModelRouting.ts  # Model routing hook
│   │   ├── useStreaming.ts     # Streaming hook
│   │   └── index.ts            # Hooks exports
│   ├── lib/                     # Utilities, services, constants
│   │   ├── services/           # API services
│   │   ├── utils/              # Utility functions
│   │   ├── constants/          # Application constants
│   │   ├── types/              # TypeScript type definitions
│   │   └── error-handler.ts    # Error handling utilities
│   ├── store/                  # State management (Zustand stores)
│   ├── theme/                  # Theme system and styling
│   │   ├── index.ts            # Theme configuration and utilities
│   │   └── components/         # Theme-aware components
│   │       └── ThemeProvider.tsx # Theme provider component
│   └── providers/              # Context providers
├── app/                        # Next.js app directory (pages/routes only)
│   ├── (auth)/                 # Auth routes
│   ├── admin/                  # Admin routes
│   ├── chat/                   # Chat routes
│   ├── dashboard/              # Dashboard routes
│   ├── globals.css             # Global styles
│   ├── layout.tsx              # Root layout
│   └── page.tsx                # Home page
├── public/                     # Static assets
└── [other files]               # Configuration files
```

## Component Organization

### UI Components (`src/components/ui/`)
- **Purpose**: Reusable UI primitives built with Radix UI
- **Examples**: Buttons, badges, tooltips, dialogs, forms
- **Naming**: PascalCase, descriptive names (e.g., `Button.tsx`, `Badge.tsx`)

### Layout Components (`src/components/layout/`)
- **Purpose**: Page layouts and structural components
- **Examples**: Header, footer, sidebar, main layout wrappers

### Feature Components (`src/components/chat/`, `dashboard/`, etc.)
- **Purpose**: Feature-specific components
- **Organization**: Grouped by feature domain
- **Naming**: Feature-specific, descriptive names

### Common Components (`src/components/common/`)
- **Purpose**: Shared business logic components
- **Examples**: Data tables, charts, forms, modals

## State Management

### Zustand Stores (`src/store/`)
- **Purpose**: Global state management
- **Organization**: Domain-specific stores
- **Examples**: `auth-store.ts`, `chat-store.ts`, `settings-store.ts`

### Context Providers (`src/providers/`)
- **Purpose**: Context-based state for specific features
- **Examples**: Auth provider, theme provider, WebSocket provider

## Services and Utilities

### API Services (`src/lib/services/`)
- **Purpose**: API communication and data fetching
- **Organization**: Domain-specific services
- **Examples**: `auth-service.ts`, `chat-service.ts`, `analytics-service.ts`

### Utilities (`src/lib/utils/`)
- **Purpose**: Helper functions and utilities
- **Organization**: Categorized by functionality
- **Examples**: `format-utils.ts`, `validation-utils.ts`, `date-utils.ts`

### Constants (`src/lib/constants/`)
- **Purpose**: Application constants and configuration
- **Examples**: API endpoints, feature flags, default values

### Types (`src/lib/types/`)
- **Purpose**: TypeScript type definitions
- **Organization**: Domain-specific type files
- **Examples**: `api.ts`, `chat.ts`, `user.ts`

## Theme System

### Design Tokens (`src/theme/index.ts`)
- **Purpose**: Centralized design system
- **Features**: Colors, spacing, typography, shadows
- **Accessibility**: High contrast mode support

### Theme Provider (`src/theme/components/ThemeProvider.tsx`)
- **Purpose**: Theme context and management
- **Features**: Theme switching, high contrast mode, localStorage persistence

## Hooks

### Custom Hooks (`src/hooks/`)
- **Purpose**: Reusable logic and state management
- **Organization**: Function-specific hooks
- **Examples**: `useApi.ts`, `useChat.ts`, `useModelRouting.ts`

## Development Guidelines

### Import Paths
- Use absolute imports from `src/` for better maintainability
- Example: `import { Button } from 'src/components/ui/Button'`

### Component Patterns
- Use functional components with TypeScript
- Follow consistent naming conventions
- Export components as default exports
- Include proper TypeScript interfaces

### State Management
- Use Zustand for global state
- Use Context for feature-specific state
- Keep state logic separate from components when possible

### Error Handling
- Use the ErrorBoundary component for error boundaries
- Implement proper error handling in services
- Use consistent error types and messages

### Testing
- Write unit tests for components and utilities
- Use integration tests for API services
- Follow testing best practices for React applications

## Migration Notes

This project was migrated from Vite to Next.js 14.2.15 with App Router. Key changes:

- **Routing**: File-based routing in `app/` directory
- **Server Components**: Default to server components, use `'use client'` for client components
- **Environment Variables**: Use `NEXT_PUBLIC_*` prefix for client-side variables
- **Build System**: Next.js with Turbopack for faster builds

## Next Steps

### Phase 2: Component Library
- [ ] Create comprehensive UI component library
- [ ] Implement consistent component patterns
- [ ] Add proper TypeScript types for all components
- [ ] Create component documentation

### Phase 3: State & Services
- [ ] Set up Zustand stores for all domains
- [ ] Organize API services by domain
- [ ] Create utility functions
- [ ] Implement proper error handling

### Phase 4: Polish & Optimization
- [ ] Performance optimization
- [ ] Accessibility improvements
- [ ] Code splitting and lazy loading
- [ ] Testing setup

## Contributing

1. Follow the established directory structure
2. Use consistent naming conventions
3. Write TypeScript for type safety
4. Add proper documentation for new features
5. Follow the existing code style and patterns
