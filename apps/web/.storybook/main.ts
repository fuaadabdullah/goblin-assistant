import type { StorybookConfig } from '@storybook/nextjs-vite';
import { fileURLToPath } from 'node:url';
import { mergeConfig } from 'vite';

const sharedSource = fileURLToPath(new URL('../../../packages/shared/src', import.meta.url));

const config: StorybookConfig = {
  stories: ['../src/**/*.mdx', '../src/**/*.stories.@(js|jsx|mjs|ts|tsx)'],
  addons: ['@chromatic-com/storybook', '@storybook/addon-docs', '@storybook/addon-onboarding'],
  framework: {
    name: '@storybook/nextjs-vite',
    options: {},
  },
  staticDirs: ['../public'],
  viteFinal: async (viteConfig) =>
    mergeConfig(viteConfig, {
      build: {
        target: 'esnext',
      },
      esbuild: {
        target: 'esnext',
      },
      resolve: {
        alias: [{ find: '@goblin/shared', replacement: sharedSource }],
      },
    }),
};

export default config;
