/** @type {import('@lhci/cli').LighthouseConfig} */
module.exports = {
  ci: {
    collect: {
      url: ['http://localhost:3000/', 'http://localhost:3000/login', 'http://localhost:3000/chat'],
      startServerCommand: 'pnpm start',
      startServerReadyPattern: 'Ready on|ready on|started server',
      startServerReadyTimeout: 30000,
      numberOfRuns: 3,
      settings: {
        chromeFlags: '--no-sandbox --disable-dev-shm-usage',
        preset: 'desktop',
        // Skip a11y — covered by dedicated accessibility.spec.ts
        skipAudits: ['color-contrast'],
      },
    },
    assert: {
      assertions: {
        // Core Web Vitals gates
        'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],
        'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
        // TBT is the lab proxy for INP; real INP measured via CrUX
        'total-blocking-time': ['error', { maxNumericValue: 600 }],
        // Overall performance score gate
        'categories:performance': ['warn', { minScore: 0.75 }],
        // Regressions in other categories surface as warnings only
        'categories:accessibility': ['warn', { minScore: 0.9 }],
        'categories:best-practices': ['warn', { minScore: 0.9 }],
        'categories:seo': ['warn', { minScore: 0.8 }],
        // Specific audit gates
        'render-blocking-resources': ['warn', { maxLength: 0 }],
        'uses-optimized-images': 'warn',
        'unused-javascript': ['warn', { maxNumericValue: 100000 }],
        'unused-css-rules': ['warn', { maxNumericValue: 50000 }],
      },
    },
    upload: {
      // Store locally in CI for artifact upload; switch to lhci server
      // or temporary-public-storage once a server is provisioned.
      target: 'filesystem',
      outputDir: '.lighthouseci',
    },
  },
};
