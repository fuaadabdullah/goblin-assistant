import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './index';
import EmptyState from './EmptyState';
import InlineErrorState from './InlineErrorState';
import PageState from './PageState';
import SectionLoadingState from './SectionLoadingState';

const meta = {
  title: 'UI/StatePrimitives',
  component: EmptyState,
  tags: ['autodocs'],
} satisfies Meta<typeof EmptyState>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Empty: Story = {
  render: () => (
    <EmptyState
      icon="📭"
      title="Nothing here yet"
      description="Create your first item to get started."
      actionLabel="Create item"
      onAction={() => undefined}
    />
  ),
};

export const InlineError: Story = {
  render: () => (
    <InlineErrorState
      title="Request failed"
      message="We could not load the latest data."
      onRetry={() => undefined}
    />
  ),
};

export const LoadingSection: Story = {
  render: () => (
    <SectionLoadingState
      label="Loading dashboard"
      description="Pulling the latest health and cost data."
    />
  ),
};

export const LoadingPage: Story = {
  render: () => (
    <PageState
      variant="loading"
      title="Loading workspace"
      description="Setting up your app shell."
    />
  ),
};

export const EmptyPage: Story = {
  render: () => (
    <PageState
      variant="empty"
      title="No conversation selected"
      description="Pick a thread or start a new one."
      actionLabel="Start chat"
      secondaryAction={<Button variant="secondary">Browse history</Button>}
    />
  ),
};

export const ErrorPage: Story = {
  render: () => (
    <PageState
      variant="error"
      title="Settings unavailable"
      description="We could not load your settings right now."
      actionLabel="Retry"
      onAction={() => undefined}
    />
  ),
};
