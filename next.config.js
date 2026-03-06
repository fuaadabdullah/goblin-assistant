/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    typescript: {
        ignoreBuildErrors: true,
    },
    eslint: {
        ignoreDuringBuilds: true,
    },
    // Expose server-side env vars needed by API routes (pages/api/*).
    serverRuntimeConfig: {
        GOBLIN_BACKEND_URL: process.env.GOBLIN_BACKEND_URL,
        LOCAL_LLM_API_KEY: process.env.LOCAL_LLM_API_KEY,
    },
    // Silence build warnings for missing optional deps
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
                    { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), gyroscope=(), accelerometer=(), magnetometer=(), payment=()' },
                ],
            },
        ];
    },
};

module.exports = nextConfig;