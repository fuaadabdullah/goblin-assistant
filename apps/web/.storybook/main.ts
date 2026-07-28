import type { StorybookConfig } from '@storybook/nextjs-vite';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mergeConfig } from 'vite';

const storybookDir = fileURLToPath(new URL('.', import.meta.url));
const repoRoot = resolve(storybookDir, '../../..');

const config: StorybookConfig = {
  stories: [
    '../src/**/*.mdx',
    '../src/**/*.stories.@(js|jsx|mjs|ts|tsx)',
    // Pull in the @goblin/ui component library stories as well
    '../../../packages/ui/src/**/*.mdx',
    '../../../packages/ui/src/**/*.stories.@(js|jsx|mjs|ts|tsx)',
  ],
  addons: [
    '@chromatic-com/storybook',
    '@storybook/addon-docs',
    '@storybook/addon-onboarding',
    '@storybook/addon-a11y',
    '@storybook/addon-themes',
  ],
  framework: {
    name: '@storybook/nextjs-vite',
    options: {},
  },
  viteFinal: async (config) =>
    mergeConfig(config, {
      build: {
        // Storybook bundles docs/a11y tooling that is intentionally not part of
        // the production app. Keep this budget scoped to Storybook so Vite's
        // runtime app warnings stay meaningful.
        chunkSizeWarningLimit: 1500,
        target: 'esnext',
      },
      resolve: {
        alias: [
          {
            find: '@goblin/ui/tokens',
            replacement: resolve(repoRoot, 'packages/ui/src/tokens/index.css'),
          },
          { find: /^@goblin\/ui$/, replacement: resolve(repoRoot, 'packages/ui/src/index.ts') },
          {
            find: /^@goblin\/shared$/,
            replacement: resolve(repoRoot, 'packages/shared/src/index.ts'),
          },
          { find: '@', replacement: resolve(storybookDir, '../src') },
        ],
      },
    }),
  staticDirs: ['../public'],
};

export default config;
