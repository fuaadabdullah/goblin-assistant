import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

const webCoverageThreshold = Number(process.env['WEB_COVERAGE_THRESHOLD'] ?? 80);
const functionCoverageThreshold = Number(process.env['WEB_FUNCTIONS_THRESHOLD'] ?? 80);
const criticalCoverageInclude = process.env['VITEST_COVERAGE_INCLUDE']
  ?.split(',')
  .map((entry) => entry.trim())
  .filter(Boolean);

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'stub-css',
      resolveId(id: string) {
        if (id.endsWith('.css') || id.endsWith('.scss') || id.endsWith('.less')) {
          return '\0' + id;
        }
      },
      load(id: string) {
        if (
          id.startsWith('\0') &&
          (id.endsWith('.css') || id.endsWith('.scss') || id.endsWith('.less'))
        ) {
          return 'export default {}';
        }
      },
    },
  ],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: [
      'e2e/**',
      'node_modules/**',
      '.next/**',
      'src/components/auth/__tests__/ModularLoginForm.test.tsx',
    ],
    css: false,
    testTimeout: 15000,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'lcov', 'json-summary'],
      include: criticalCoverageInclude ?? ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/**/*.spec.{ts,tsx}',
        'src/**/__tests__/**',
        'src/**/*.stories.{ts,tsx}',
        'src/**/*.d.ts',
        'src/**/index.ts',
        'src/test/**',
        'src/__mocks__/**',
        'src/stories/**',
        'src/types/**',
        'src/theme/**',
        'src/content/**',
      ],
      thresholds: {
        statements: webCoverageThreshold,
        branches: webCoverageThreshold,
        functions: functionCoverageThreshold,
        lines: webCoverageThreshold,
      },
    },
  },
  resolve: {
    alias: [
      { find: '@', replacement: path.resolve(__dirname, 'src') },
      { find: '@goblin/shared', replacement: path.resolve(__dirname, '../../packages/shared/src') },
      {
        find: 'lucide-react',
        replacement: path.resolve(__dirname, 'src/__mocks__/lucide-react.tsx'),
      },
    ],
  },
});
