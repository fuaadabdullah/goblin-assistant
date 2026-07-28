import type { Preview } from '@storybook/nextjs';
import { useEffect, type ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { ProviderProvider } from '../src/contexts/ProviderContext';
import { ContrastModeProvider } from '../src/hooks/useContrastMode';
import { createQueryClient } from '../src/lib/queryClient';
import '../src/index.css';
import 'highlight.js/styles/github-dark.css';

const queryClient = createQueryClient();

const Providers = ({ children, theme }: { children: ReactNode; theme?: string }) => {
  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('goblinos-light', theme === 'light');
    root.classList.toggle('goblinos-high-contrast', theme === 'high-contrast');
  }, [theme]);

  return (
    <QueryClientProvider client={queryClient}>
      <ProviderProvider>
        <ContrastModeProvider>{children}</ContrastModeProvider>
      </ProviderProvider>
    </QueryClientProvider>
  );
};

const preview: Preview = {
  decorators: [
    (Story, context) => (
      <Providers theme={context.globals['theme'] as string}>
        <div className="min-h-screen bg-bg p-6 text-text">
          <Story />
        </div>
      </Providers>
    ),
  ],
  globalTypes: {
    theme: {
      description: 'Design system theme',
      toolbar: {
        icon: 'circlehollow',
        items: [
          { value: 'dark', title: 'Dark' },
          { value: 'light', title: 'Light' },
          { value: 'high-contrast', title: 'High Contrast' },
        ],
      },
    },
  },
  initialGlobals: {
    theme: 'dark',
  },
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    layout: 'centered',
  },
};

export default preview;
