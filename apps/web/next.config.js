/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    externalDir: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Expose server-side env vars needed by API routes (pages/api/*).
  serverRuntimeConfig: {
    GOBLIN_BACKEND_URL: process.env.GOBLIN_BACKEND_URL,
    LOCAL_LLM_API_KEY: process.env.LOCAL_LLM_API_KEY,
  },
  // Next.js 16 uses Turbopack by default — empty config silences the "webpack but no turbopack" error
  turbopack: {},
  // Webpack fallback for non-Turbopack builds
  webpack: (config) => {
    config.resolve.fallback = { ...config.resolve.fallback, fs: false };
    return config;
  },
  // Security headers
  async rewrites() {
    return [
      { source: '/', destination: '/home' },
      { source: '/chat', destination: '/chat/chat-page' },
      { source: '/search', destination: '/chat/search-page' },
      { source: '/login', destination: '/auth/login' },
      { source: '/register', destination: '/auth/register' },
      { source: '/google-callback', destination: '/auth/google-callback' },
      { source: '/account', destination: '/app/account' },
      { source: '/help', destination: '/app/help' },
      { source: '/settings', destination: '/app/settings' },
      { source: '/onboarding', destination: '/orchestration/onboarding' },
      { source: '/sandbox', destination: '/orchestration/sandbox' },
      { source: '/startup', destination: '/orchestration/startup' },
    ];
  },

  // Security headers
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'X-DNS-Prefetch-Control', value: 'on' },
          {
            key: 'Permissions-Policy',
            value:
              'camera=(), microphone=(), geolocation=(), gyroscope=(), accelerometer=(), magnetometer=(), payment=()',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
