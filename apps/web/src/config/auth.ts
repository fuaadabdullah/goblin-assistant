// src/config/auth.ts - New file
import { env } from './env';

export const AUTH_CONFIG = {
  // Use httpOnly cookies instead of localStorage
  USE_COOKIES: true,
  TOKEN_COOKIE_NAME: 'session_token',
  REFRESH_COOKIE_NAME: 'refresh_token',
  // Fallback for development only
  ALLOW_LOCALSTORAGE_DEV: env.isDevelopment,
} as const;
