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
  setupFilesAfterSetup: ['<rootDir>/jest.setup.ts'],
  collectCoverage: true,
  coverageDirectory: 'coverage',
  coverageProvider: 'v8',
  testPathIgnorePatterns: [
    '/node_modules/',
    '/\\._.*$/',
  ],
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '<rootDir>/.next/',
    '<rootDir>/coverage/',
    '/\\._.*$/',
  ],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
};

module.exports = hasNextJest
  ? createJestConfig(customJestConfig)
  : customJestConfig;
