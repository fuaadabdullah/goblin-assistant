import type { StorybookConfig } from '@storybook/nextjs-vite';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { mergeConfig } from 'vite';

const storybookDir = path.dirname(fileURLToPath(import.meta.url));

const config: StorybookConfig = {
  stories: ['../src/**/*.mdx', '../src/**/*.stories.@(js|jsx|mjs|ts|tsx)'],
  addons: ['@chromatic-com/storybook', '@storybook/addon-docs', '@storybook/addon-onboarding'],
  framework: {
    name: '@storybook/nextjs-vite',
    options: {},
  },
  staticDirs: ['../public'],
  viteFinal: async (config) =>
    mergeConfig(config, {
      build: {
        target: 'esnext',
      },
      resolve: {
        alias: [
          { find: '@', replacement: path.resolve(storybookDir, '../src') },
          {
            find: '@goblin/shared',
            replacement: path.resolve(storybookDir, '../../../packages/shared/src'),
          },
          {
            find: '@goblin/ui',
            replacement: path.resolve(storybookDir, '../../../packages/ui/src'),
          },
        ],
      },
    }),
};

export default config;
