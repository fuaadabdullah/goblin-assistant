import {
  DEFAULT_BACKEND_ORIGIN,
  resolveBackendOrigin,
  resolvePublicBackendOrigin,
} from '../../config/backendOrigin';

describe('backend origin resolution', () => {
  it('uses server-only backend origin first and normalizes trailing slash', () => {
    const env = {
      GOBLIN_BACKEND_URL: 'https://goblin.example/',
      NEXT_PUBLIC_API_BASE_URL: 'https://public.example',
    } as NodeJS.ProcessEnv;

    expect(resolveBackendOrigin(env)).toBe('https://goblin.example');
  });

  it('falls back to BACKEND_URL when GOBLIN_BACKEND_URL is missing', () => {
    const env = {
      BACKEND_URL: 'https://backend.example',
      NEXT_PUBLIC_API_BASE_URL: 'https://public.example',
    } as NodeJS.ProcessEnv;

    expect(resolveBackendOrigin(env)).toBe('https://backend.example');
  });

  it('uses only NEXT_PUBLIC vars for public resolver', () => {
    const env = {
      GOBLIN_BACKEND_URL: 'https://private.example',
      NEXT_PUBLIC_BACKEND_URL: 'https://public-backend.example',
    } as NodeJS.ProcessEnv;

    expect(resolvePublicBackendOrigin(env)).toBe('https://public-backend.example');
  });

  it('returns shared default when no backend env var is set', () => {
    const env = {} as NodeJS.ProcessEnv;

    expect(resolveBackendOrigin(env)).toBe(DEFAULT_BACKEND_ORIGIN);
    expect(resolvePublicBackendOrigin(env)).toBe(DEFAULT_BACKEND_ORIGIN);
  });
});
