const fs = require('fs');
const path = require('path');

const appVersion = fs.readFileSync(path.join(__dirname, '../../VERSION'), 'utf8').trim();

/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_APP_VERSION: appVersion,
  },
  reactStrictMode: true,
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
        ],
      },
    ];
  },
};

module.exports = nextConfig;
