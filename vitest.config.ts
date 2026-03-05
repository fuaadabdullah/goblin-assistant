import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    // Use jsdom for DOM environment
    environment: 'jsdom',

    // Setup test files
    setupFiles: ['./src/test/setup.ts'],

    // Make testing utilities available globally without imports
    globals: true,

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'html', 'json', 'lcov', 'xml'],
      reportsDirectory: './coverage',
      exclude: [
        'node_modules/',
        'src/test/',
        '.next/',
        'dist/',
        '**/*.config.ts',
        '**/*.config.js',
        '**/types.ts',
        '**/types.d.ts',
        'src/**/*.test.tsx',
        'src/**/*.test.ts',
        'src/**/*.spec.tsx',
        'src/**/*.spec.ts',
      ],
      all: true,
      lines: 80,
      functions: 80,
      branches: 80,
      statements: 80,
    },

    // Include test files
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
