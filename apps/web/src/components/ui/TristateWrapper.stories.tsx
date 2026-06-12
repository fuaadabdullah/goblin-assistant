import type { Meta, StoryObj } from '@storybook/react';
import TristateWrapper from './TristateWrapper';
import { Button } from './index';

const meta = {
  title: 'UI/TristateWrapper',
  component: TristateWrapper,
  tags: ['autodocs'],
} satisfies Meta<typeof TristateWrapper>;

export default meta;
type Story = StoryObj<typeof meta>;

export const LoadingPage: Story = {
  args: {
    loading: true,
    loadingTitle: 'Loading dashboard',
    loadingDescription: 'Pulling the latest health and cost data.',
    children: <div className="p-4 text-text">Dashboard content</div>,
  },
};

export const LoadingSection: Story = {
  args: {
    loading: true,
    plain: true,
    loadingTitle: 'Loading section',
    loadingDescription: 'Fetching items for this panel.',
    children: <div className="p-4 text-text">Section content</div>,
  },
};

export const ErrorPage: Story = {
  args: {
    error: 'Connection lost. Please check your network.',
    errorTitle: 'Network error',
    onRetry: () => undefined,
    retryLabel: 'Try again',
    children: <div className="p-4 text-text">Settings content</div>,
  },
};

export const ErrorSection: Story = {
  args: {
    error: new Error('Failed to fetch provider list'),
    plain: true,
    onRetry: () => undefined,
    children: <div className="p-4 text-text">Provider list</div>,
  },
};

export const ErrorWithCustomChild: Story = {
  args: {
    error: 'Something broke',
    errorChild: (
      <div className="rounded-md border border-red-400 bg-red-50 p-6 text-center">
        <p className="font-semibold text-red-800">⚠️ Custom error UI</p>
        <p className="mt-1 text-sm text-red-600">
          This uses errorChild instead of the built-in error state.
        </p>
      </div>
    ),
    children: <div className="p-4 text-text">Content</div>,
  },
};

export const EmptyPage: Story = {
  args: {
    empty: true,
    emptyTitle: 'No conversations yet',
    emptyDescription: 'Start a new chat to begin tracking your AI interactions.',
    emptyActionLabel: 'Start chat',
    onEmptyAction: () => undefined,
    emptyIcon: '💬',
    children: <div className="p-4 text-text">Chat list</div>,
  },
};

export const EmptySection: Story = {
  args: {
    empty: true,
    plain: true,
    emptyTitle: 'No results found',
    emptyDescription: 'Try adjusting your filters or search query.',
    emptyActionLabel: 'Clear filters',
    onEmptyAction: () => undefined,
    children: <div className="p-4 text-text">Search results</div>,
  },
};

export const EmptyWithSecondaryAction: Story = {
  args: {
    empty: true,
    plain: true,
    emptyTitle: 'No providers configured',
    emptyDescription: 'Add a provider key on the backend before saving model preferences.',
    emptySecondaryAction: (
      <Button variant="secondary" onClick={() => undefined}>
        View docs
      </Button>
    ),
    children: <div className="p-4 text-text">Provider settings</div>,
  },
};

export const ContentRendered: Story = {
  args: {
    loading: false,
    empty: false,
    error: undefined,
    children: (
      <div className="space-y-2 rounded-lg bg-surface p-6 text-text">
        <h2 className="text-xl font-bold">Dashboard Content</h2>
        <p>This content is shown when loading, error, and empty are all falsy.</p>
      </div>
    ),
  },
};

export const AllStates: Story = {
  render: () => (
    <div className="space-y-8">
      <section>
        <h3 className="mb-2 text-sm font-semibold text-muted">LOADING</h3>
        <TristateWrapper loading plain loadingTitle="Loading providers">
          <div />
        </TristateWrapper>
      </section>
      <section>
        <h3 className="mb-2 text-sm font-semibold text-muted">ERROR</h3>
        <TristateWrapper error="Something went wrong" plain onRetry={() => undefined}>
          <div />
        </TristateWrapper>
      </section>
      <section>
        <h3 className="mb-2 text-sm font-semibold text-muted">EMPTY</h3>
        <TristateWrapper empty plain emptyTitle="No items">
          <div />
        </TristateWrapper>
      </section>
      <section>
        <h3 className="mb-2 text-sm font-semibold text-muted">CONTENT</h3>
        <TristateWrapper>
          <div className="rounded-lg bg-primary/10 p-4 text-center text-primary">
            ✅ Content loaded successfully
          </div>
        </TristateWrapper>
      </section>
    </div>
  ),
};
