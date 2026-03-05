import type { Meta, StoryObj } from '@storybook/react';
import { CheckCircle, AlertTriangle, XCircle, Info } from 'lucide-react';
import Badge from './Badge';

const meta = {
  title: 'UI/Badge',
  component: Badge,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['success', 'warning', 'danger', 'neutral'],
    },
    size: {
      control: 'select',
      options: ['sm', 'md'],
    },
  },
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Success: Story = {
  args: {
    children: 'Success',
    variant: 'success',
  },
};

export const Warning: Story = {
  args: {
    children: 'Warning',
    variant: 'warning',
  },
};

export const Danger: Story = {
  args: {
    children: 'Error',
    variant: 'danger',
  },
};

export const Neutral: Story = {
  args: {
    children: 'Info',
    variant: 'neutral',
  },
};

export const Small: Story = {
  args: {
    children: 'Small Badge',
    size: 'sm',
  },
};

export const WithIconSuccess: Story = {
  args: {
    children: 'Online',
    variant: 'success',
    icon: <CheckCircle size={14} />,
  },
};

export const WithIconWarning: Story = {
  args: {
    children: 'Degraded',
    variant: 'warning',
    icon: <AlertTriangle size={14} />,
  },
};

export const WithIconDanger: Story = {
  args: {
    children: 'Offline',
    variant: 'danger',
    icon: <XCircle size={14} />,
  },
};

export const WithIconNeutral: Story = {
  args: {
    children: 'Unknown',
    variant: 'neutral',
    icon: <Info size={14} />,
  },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap gap-3">
      <Badge variant="success">Success</Badge>
      <Badge variant="warning">Warning</Badge>
      <Badge variant="danger">Danger</Badge>
      <Badge variant="neutral">Neutral</Badge>
    </div>
  ),
  args: {
    children: 'Badge',
  },
};

export const StatusBadges: Story = {
  render: () => (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2 items-center">
        <span className="text-sm text-gray-300 w-20">Small:</span>
        <Badge size="sm" variant="success" icon={<CheckCircle size={12} />}>
          Healthy
        </Badge>
        <Badge size="sm" variant="warning" icon={<AlertTriangle size={12} />}>
          Degraded
        </Badge>
        <Badge size="sm" variant="danger" icon={<XCircle size={12} />}>
          Down
        </Badge>
      </div>
      <div className="flex gap-2 items-center">
        <span className="text-sm text-gray-300 w-20">Medium:</span>
        <Badge size="md" variant="success" icon={<CheckCircle size={14} />}>
          Healthy
        </Badge>
        <Badge size="md" variant="warning" icon={<AlertTriangle size={14} />}>
          Degraded
        </Badge>
        <Badge size="md" variant="danger" icon={<XCircle size={14} />}>
          Down
        </Badge>
      </div>
    </div>
  ),
  args: {
    children: 'Badge',
  },
};
