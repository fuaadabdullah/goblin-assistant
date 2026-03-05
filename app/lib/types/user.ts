// lib/types/user.ts
export interface User {
  id: string;
  email: string;
  name?: string;
  avatar?: string;
  preferences: UserPreferences;
  createdAt: Date;
  lastLoginAt?: Date;
  isActive: boolean;
  subscription?: SubscriptionInfo;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  timezone: string;
  notifications: NotificationSettings;
  routingStrategy: import('./providers').RoutingStrategy;
  defaultProvider?: string;
  defaultModel?: string;
  maxTokensPerRequest?: number;
  streamingEnabled: boolean;
}

export interface NotificationSettings {
  email: boolean;
  push: boolean;
  costAlerts: boolean;
  usageReports: boolean;
  errorAlerts: boolean;
}

export interface SubscriptionInfo {
  plan: 'free' | 'pro' | 'enterprise';
  status: 'active' | 'inactive' | 'cancelled' | 'past_due';
  currentPeriodStart: Date;
  currentPeriodEnd: Date;
  limits: {
    monthlyRequests: number;
    monthlyTokens: number;
    maxCostPerMonth: number;
  };
  features: string[];
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  sessionToken?: string;
  refreshToken?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  name?: string;
  acceptTerms: boolean;
}

export interface OAuthCallback {
  code: string;
  state?: string;
  provider: 'google' | 'github' | 'microsoft';
}
