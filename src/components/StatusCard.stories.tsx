import type { Meta, StoryObj } from '@storybook/react';
import { Database, Server, Cloud, Activity } from 'lucide-react';
import StatusCard from './StatusCard';

const meta = {
  title: 'Components/StatusCard',
  component: StatusCard,
  parameters: {
    layout: 'padded',
  },
  tags: ['autodocs'],
  argTypes: {
    status: {
      control: 'select',
      options: ['healthy', 'degraded', 'down', 'unknown'],
    },
  },
} satisfies Meta<typeof StatusCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Healthy: Story = {
  args: {
    title: 'API Server',
    status: 'healthy',
    icon: <Server />,
    lastCheck: '2 minutes ago',
  },
};

export const Degraded: Story = {
  args: {
    title: 'Database',
    status: 'degraded',
    icon: <Database />,
    lastCheck: '1 minute ago',
    statusDetails: 'High response times detected',
  },
};

export const Down: Story = {
  args: {
    title: 'Cloud Storage',
    status: 'down',
    icon: <Cloud />,
    lastCheck: '5 minutes ago',
    statusDetails: 'Connection timeout',
  },
};

export const Unknown: Story = {
  args: {
    title: 'Monitoring Service',
    status: 'unknown',
    icon: <Activity />,
    lastCheck: '30 seconds ago',
  },
};

export const WithMetadata: Story = {
  args: {
    title: 'API Gateway',
    status: 'healthy',
    icon: <Server />,
    lastCheck: '1 minute ago',
    meta: [
      { label: 'Uptime', value: '99.9%' },
      { label: 'Requests/min', value: '1,234' },
      { label: 'Avg Response', value: '45ms' },
    ],
  },
};

export const MinimalCard: Story = {
  args: {
    title: 'Basic Service',
    status: 'healthy',
  },
};

export const AllStatuses: Story = {
  render: () => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <StatusCard
        title="API Server"
        status="healthy"
        icon={<Server />}
        lastCheck="2 minutes ago"
        meta={[
          { label: 'Uptime', value: '99.9%' },
          { label: 'Requests/min', value: '1,234' },
        ]}
      />
      <StatusCard
        title="Database"
        status="degraded"
        icon={<Database />}
        lastCheck="1 minute ago"
        statusDetails="High latency detected"
        meta={[{ label: 'Connections', value: '45/50' }]}
      />
      <StatusCard
        title="Cloud Storage"
        status="down"
        icon={<Cloud />}
        lastCheck="5 minutes ago"
        statusDetails="Connection timeout"
      />
      <StatusCard
        title="Monitoring"
        status="unknown"
        icon={<Activity />}
        lastCheck="30 seconds ago"
      />
    </div>
  ),
  args: {
    title: 'API Server',
    status: 'healthy',
  },
};
