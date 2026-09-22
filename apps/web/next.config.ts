import type { NextConfig } from 'next';
import fs from 'fs';
import path from 'path';

const appVersion = fs.readFileSync(path.join(__dirname, '../../VERSION'), 'utf8').trim();
const isProduction = process.env.NODE_ENV === 'production';

const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "form-action 'self'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
  `script-src 'self' 'unsafe-inline'${isProduction ? '' : " 'unsafe-eval'"}`,
  "connect-src 'self' https: wss:",
  "worker-src 'self' blob:",
  "manifest-src 'self'",
  ...(isProduction ? ['upgrade-insecure-requests'] : []),
].join('; ');

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_APP_VERSION: appVersion,
  },
  // Strip console.warn in production builds; console.error is preserved for error reporting
  compiler: {
    removeConsole: {
      exclude: ['error'],
    },
  },
  reactStrictMode: true,
  transpilePackages: ['@goblin/ui'],
  images: {
    // Serve AVIF first (best compression), fall back to WebP, then original.
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    minimumCacheTTL: 604800,
  },
  experimental: {
    externalDir: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  // Next.js 16 uses Turbopack by default — empty config silences the "webpack but no turbopack" error
  turbopack: {},
  // Webpack fallback for non-Turbopack builds
  webpack: (config) => {
    config.resolve.fallback = { ...config.resolve.fallback, fs: false };
    return config;
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
          { key: 'Content-Security-Policy', value: contentSecurityPolicy },
        ],
      },
    ];
  },
};

export default nextConfig;
