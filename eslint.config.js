// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import storybook from "eslint-plugin-storybook";

import js from '@eslint/js';
import tseslint from '@typescript-eslint/eslint-plugin';
import tsparser from '@typescript-eslint/parser';

export default [js.configs.recommended, {
  files: ['**/*.{ts,tsx}'],
  languageOptions: {
    parser: tsparser,
    parserOptions: {
      ecmaVersion: 2020,
      sourceType: 'module',
      ecmaFeatures: {
        jsx: true,
      },
    },
    globals: {
      // Browser globals
      console: 'readonly',
      process: 'readonly',
      Buffer: 'readonly',
      __dirname: 'readonly',
      __filename: 'readonly',
      RequestInit: 'readonly',
      EventSource: 'readonly',
      window: 'readonly',
      document: 'readonly',
      navigator: 'readonly',
      fetch: 'readonly',
      URL: 'readonly',
      URLSearchParams: 'readonly',
      FormData: 'readonly',
      Headers: 'readonly',
      Response: 'readonly',
      Request: 'readonly',
      Event: 'readonly',
      CustomEvent: 'readonly',
      HTMLElement: 'readonly',
      HTMLInputElement: 'readonly',
      HTMLButtonElement: 'readonly',
      HTMLDivElement: 'readonly',
      HTMLFormElement: 'readonly',
      HTMLTextAreaElement: 'readonly',
      HTMLParagraphElement: 'readonly',
      HTMLHeadingElement: 'readonly',
      HTMLLabelElement: 'readonly',
      HTMLImageElement: 'readonly',
      HTMLScriptElement: 'readonly',
      HTMLLinkElement: 'readonly',
      KeyboardEvent: 'readonly',
      EventTarget: 'readonly',
      TextDecoder: 'readonly',
      WebSocket: 'readonly',
      Image: 'readonly',
      StorageEvent: 'readonly',
      NodeJS: 'readonly',
      performance: 'readonly',
      cancelAnimationFrame: 'readonly',
      PerformanceObserver: 'readonly',
      PerformanceNavigationTiming: 'readonly',
      PerformanceResourceTiming: 'readonly',
      MutationObserver: 'readonly',
      IntersectionObserver: 'readonly',
      localStorage: 'readonly',
      sessionStorage: 'readonly',
      setTimeout: 'readonly',
      clearTimeout: 'readonly',
      setInterval: 'readonly',
      clearInterval: 'readonly',
      requestAnimationFrame: 'readonly',
      btoa: 'readonly',
      atob: 'readonly',
      React: 'readonly',
    },
  },
  plugins: {
    '@typescript-eslint': tseslint,
  },
  rules: {
    // TypeScript specific rules
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/explicit-function-return-type': 'off',
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    '@typescript-eslint/no-explicit-any': 'warn',

    // General rules
    'no-console': 'off', // We handle this with dev-log utility
    'no-debugger': 'error',
    'no-alert': 'error',
    'no-eval': 'error',
    'no-implied-eval': 'error',
    'no-new-func': 'error',
    'no-script-url': 'error',
    'no-sequences': 'error',
  },
}, {
  files: ['scripts/**/*.{ts,js}', 'tools/**/*.{ts,js}'],
  languageOptions: {
    globals: {
      // Node.js globals for scripts
      console: 'readonly',
      process: 'readonly',
      Buffer: 'readonly',
      __dirname: 'readonly',
      __filename: 'readonly',
      require: 'readonly',
      module: 'readonly',
      exports: 'readonly',
      global: 'readonly',
      setTimeout: 'readonly',
      clearTimeout: 'readonly',
      setInterval: 'readonly',
      clearInterval: 'readonly',
    },
  },
  rules: {
    'no-console': 'off',
    '@typescript-eslint/no-var-requires': 'off',
  },
}, {
  ignores: [
    'dist/',
    'node_modules/',
    'build/',
    '.storybook-out/',
    'coverage/',
    '*.config.js',
    '*.config.ts',
  ],
}, ...storybook.configs["flat/recommended"]];
