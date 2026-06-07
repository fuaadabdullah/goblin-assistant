import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

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
        if (id.startsWith('\0') && (id.endsWith('.css') || id.endsWith('.scss') || id.endsWith('.less'))) {
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
    exclude: ['e2e/**', 'node_modules/**', '.next/**'],
    css: false,
    testTimeout: 15000,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'lcov', 'json-summary'],
      include: ['src/**/*.{ts,tsx}'],
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
        statements: 70,
        branches: 70,
        functions: 70,
        lines: 70,
      },
    },
  },
  resolve: {
    alias: [
      { find: '@', replacement: path.resolve(__dirname, 'src') },
      { find: 'lucide-react', replacement: path.resolve(__dirname, 'src/__mocks__/lucide-react.tsx') },
    ],
  },
});
