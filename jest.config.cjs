let createJestConfig = config => config;
let hasNextJest = false;

try {
  const nextJest = require('next/jest');
  createJestConfig = nextJest({ dir: './' });
  hasNextJest = true;
} catch {
  // Fallback for environments where next is unavailable during test bootstrap.
}

const customJestConfig = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  collectCoverage: true,
  coverageDirectory: 'coverage',
  coverageProvider: 'v8',
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.test.{ts,tsx}',
    '!src/**/*.spec.{ts,tsx}',
    '!src/**/__tests__/**',
    '!src/**/*.stories.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/index.ts',
    '!src/test/**',
    '!src/__mocks__/**',
    '!src/stories/**',
    '!src/types/**',
    '!src/theme/**',
    '!src/content/**',
  ],
  coverageReporters: ['text', 'text-summary', 'lcov', 'json-summary'],
  coverageThreshold: {
    global: {
      statements: 70,
      branches: 70,
      functions: 70,
      lines: 70,
    },
  },
  testPathIgnorePatterns: [
    '/node_modules/',
    '[\\/]\\._.*$',
    '<rootDir>/e2e/',
  ],
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '<rootDir>/.next/',
    '<rootDir>/coverage/',
    '[\\/]\\._.*$',
  ],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@tanstack/query-core$': '<rootDir>/node_modules/@tanstack/query-core/build/modern/index.cjs',
    '\\.css$': '<rootDir>/src/__mocks__/styleMock.js',
  },
};

module.exports = hasNextJest
  ? createJestConfig(customJestConfig)
  : customJestConfig;
