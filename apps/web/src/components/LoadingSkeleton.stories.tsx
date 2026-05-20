import type { Meta, StoryObj } from '@storybook/react';
import {
  StatusCardSkeleton,
  StatCardSkeleton,
  ListSkeleton,
  ListItemSkeleton,
  ProviderCardSkeleton,
  DashboardSkeleton,
} from './LoadingSkeleton';

const meta = {
  title: 'Components/LoadingSkeleton',
  component: StatusCardSkeleton,
  parameters: {
    layout: 'padded',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof StatusCardSkeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const StatusCard: Story = {
  render: () => <StatusCardSkeleton />,
};

export const StatCard: Story = {
  render: () => <StatCardSkeleton />,
};

export const ListItem: Story = {
  render: () => <ListItemSkeleton />,
};

export const ListOfThree: Story = {
  render: () => <ListSkeleton count={3} />,
};

export const ListOfFive: Story = {
  render: () => <ListSkeleton count={5} />,
};

export const ProviderCard: Story = {
  render: () => <ProviderCardSkeleton />,
};

export const FullDashboard: Story = {
  render: () => <DashboardSkeleton />,
};

export const AllSkeletons: Story = {
  render: () => (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold text-gray-200 mb-4">Status Cards</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StatusCardSkeleton />
          <StatusCardSkeleton />
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-200 mb-4">Stat Cards</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-200 mb-4">Provider Cards</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <ProviderCardSkeleton />
          <ProviderCardSkeleton />
          <ProviderCardSkeleton />
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-200 mb-4">List Items</h3>
        <ListSkeleton count={5} />
      </div>
    </div>
  ),
};

export const LoadingStates: Story = {
  render: () => (
    <div className="space-y-6">
      <div className="space-y-2">
        <p className="text-sm text-gray-400">Loading dashboard...</p>
        <DashboardSkeleton />
      </div>
    </div>
  ),
};
