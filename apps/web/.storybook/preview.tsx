import type { Preview } from '@storybook/nextjs';
import type { ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from '../src/contexts/ToastContext';
import { ProviderProvider } from '../src/contexts/ProviderContext';
import { ContrastModeProvider } from '../src/hooks/useContrastMode';
import { createQueryClient } from '../src/lib/queryClient';
import '../src/index.css';
import '../src/theme/index.css';
import 'highlight.js/styles/github-dark.css';

const queryClient = createQueryClient();

const Providers = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ToastProvider>
      <ProviderProvider>
        <ContrastModeProvider>{children}</ContrastModeProvider>
      </ProviderProvider>
    </ToastProvider>
  </QueryClientProvider>
);

const preview: Preview = {
  decorators: [
    (Story) => (
      <Providers>
        <div className="min-h-screen bg-bg p-6 text-text">
          <Story />
        </div>
      </Providers>
    ),
  ],
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
