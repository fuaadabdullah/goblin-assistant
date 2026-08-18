import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const envExamplePath = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../../.env.example'
);

const parseEnvKeys = (content: string): Set<string> => {
  const keys = new Set<string>();

  content.split('\n').forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) return;

    const [key] = trimmed.split('=', 1);
    if (key) keys.add(key);
  });

  return keys;
};

describe('apps/web/.env.example', () => {
  it('covers the public web environment keys used by the app', () => {
    const content = readFileSync(envExamplePath, 'utf-8');
    const keys = parseEnvKeys(content);

    expect(keys).toEqual(
      new Set([
        'NEXT_PUBLIC_API_BASE_URL',
        'NEXT_PUBLIC_BACKEND_URL',
        'NEXT_PUBLIC_FASTAPI_URL',
        'NEXT_PUBLIC_API_URL',
        'NEXT_PUBLIC_ENABLE_DEBUG',
        'NEXT_PUBLIC_FEATURE_RAG_ENABLED',
        'NEXT_PUBLIC_FEATURE_MULTI_PROVIDER',
        'NEXT_PUBLIC_FEATURE_PASSKEY_AUTH',
        'NEXT_PUBLIC_FEATURE_GOOGLE_AUTH',
        'NEXT_PUBLIC_FEATURE_SANDBOX',
        'NEXT_PUBLIC_FEATURE_SEARCH',
        'NEXT_PUBLIC_FEATURE_ADMIN',
        'NEXT_PUBLIC_DEBUG_MODE',
        'NEXT_PUBLIC_TURNSTILE_SITE_KEY_CHAT',
        'NEXT_PUBLIC_TURNSTILE_SITE_KEY_LOGIN',
        'NEXT_PUBLIC_TURNSTILE_SITE_KEY_SEARCH',
        'NEXT_PUBLIC_SUPABASE_URL',
        'NEXT_PUBLIC_SUPABASE_ANON_KEY',
        'NEXT_PUBLIC_SENTRY_DSN',
        'NEXT_PUBLIC_GA_MEASUREMENT_ID',
        'NEXT_PUBLIC_DD_APPLICATION_ID',
        'NEXT_PUBLIC_DD_CLIENT_TOKEN',
        'NEXT_PUBLIC_DD_SITE',
        'NEXT_PUBLIC_DD_ENV',
        'NEXT_PUBLIC_DD_VERSION',
        'NEXT_PUBLIC_SITE_URL',
        'NEXT_PUBLIC_ADMIN_EMAILS',
        'NEXT_PUBLIC_ADMIN_DOMAINS',
      ])
    );
  });
});