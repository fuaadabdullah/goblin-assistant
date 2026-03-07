export const DEFAULT_BACKEND_ORIGIN = 'https://goblin-assistant-backend.onrender.com';

const cleanUrl = (value?: string): string => (value || '').trim().replace(/\/+$/, '');

const firstDefinedOrigin = (...values: Array<string | undefined>): string => {
  for (const value of values) {
    const cleaned = cleanUrl(value);
    if (cleaned) return cleaned;
  }
  return '';
};

export const resolvePublicBackendOrigin = (
  env: NodeJS.ProcessEnv = process.env,
): string =>
  firstDefinedOrigin(
    env.NEXT_PUBLIC_BACKEND_URL,
    env.NEXT_PUBLIC_FASTAPI_URL,
    env.NEXT_PUBLIC_API_URL,
    env.NEXT_PUBLIC_API_BASE_URL,
  ) || DEFAULT_BACKEND_ORIGIN;

export const resolveBackendOrigin = (env: NodeJS.ProcessEnv = process.env): string =>
  firstDefinedOrigin(
    env.GOBLIN_BACKEND_URL,
    env.BACKEND_URL,
    env.NEXT_PUBLIC_BACKEND_URL,
    env.NEXT_PUBLIC_FASTAPI_URL,
    env.NEXT_PUBLIC_API_URL,
    env.NEXT_PUBLIC_API_BASE_URL,
  ) || DEFAULT_BACKEND_ORIGIN;
