/**
 * Turnstile configuration
 *
 * SECURITY NOTE:
 * - Only PUBLIC site keys should be in VITE_ env vars
 * - SECRET keys must NEVER be in frontend code
 * - Secret keys are used only in backend verification
 */

import { env } from './env';

interface TurnstileConfig {
  siteKey: string;
  enabled: boolean;
}

function getTurnstileSiteKey(context: 'chat' | 'login' | 'search'): string {
  const siteKey = env.turnstile[context];

  // Validation: Turnstile site keys start with '0x'
  if (siteKey && !siteKey.startsWith('0x')) {
    console.error(`⚠️  Invalid Turnstile key format for ${context}`);
    throw new Error('Invalid Turnstile configuration');
  }

  // Validation: Secret keys would be longer and have different format
  if (siteKey && siteKey.includes('secret')) {
    console.error('🚨 SECRET KEY DETECTED IN CLIENT CODE!');
    throw new Error('Security violation: Secret key in client');
  }

  return siteKey;
}

export const TURNSTILE_CONFIG: Record<string, TurnstileConfig> = {
  chat: {
    siteKey: getTurnstileSiteKey('chat'),
    enabled: Boolean(env.turnstile.chat),
  },
  login: {
    siteKey: getTurnstileSiteKey('login'),
    enabled: Boolean(env.turnstile.login),
  },
  search: {
    siteKey: getTurnstileSiteKey('search'),
    enabled: Boolean(env.turnstile.search),
  },
};

// Usage
export function useTurnstile(context: 'chat' | 'login' | 'search') {
  const config = TURNSTILE_CONFIG[context];

  if (!config.enabled) {
    console.warn(`Turnstile not configured for ${context}`);
  }

  return config;
}
