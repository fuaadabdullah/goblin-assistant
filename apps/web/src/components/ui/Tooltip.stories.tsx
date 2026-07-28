import type { Meta, StoryObj } from '@storybook/react';
import { HelpCircle } from 'lucide-react';
import { Button, IconButton } from '@goblin/ui';
import Tooltip from './Tooltip';

const meta = {
  title: 'UI/Tooltip',
  component: Tooltip,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    position: {
      control: 'select',
      options: ['top', 'bottom', 'left', 'right'],
    },
  },
} satisfies Meta<typeof Tooltip>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    content: 'This is a helpful tooltip',
    children: <Button variant="secondary">Hover me</Button>,
  },
};

export const Top: Story = {
  args: {
    content: 'Tooltip appears above',
    position: 'top',
    children: <Button variant="secondary">Hover me</Button>,
  },
};

export const Bottom: Story = {
  args: {
    content: 'Tooltip appears below',
    position: 'bottom',
    children: <Button variant="secondary">Hover me</Button>,
  },
};

export const Left: Story = {
  args: {
    content: 'Tooltip appears left',
    position: 'left',
    children: <Button variant="secondary">Hover me</Button>,
  },
};

export const Right: Story = {
  args: {
    content: 'Tooltip appears right',
    position: 'right',
    children: <Button variant="secondary">Hover me</Button>,
  },
};

export const WithIcon: Story = {
  args: {
    content: 'Click for more information',
    children: <IconButton variant="ghost" icon={<HelpCircle size={20} />} aria-label="Help" />,
  },
};

export const LongContent: Story = {
  args: {
    content:
      'This tooltip contains a longer message that might span multiple lines. It provides detailed information to help users understand the feature.',
    children: <Button variant="secondary">Hover for details</Button>,
  },
};

export const AllPositions: Story = {
  render: () => (
    <div className="flex flex-col gap-8 items-center">
      <Tooltip content="Top position" position="top">
        <Button variant="secondary">Top</Button>
      </Tooltip>
      <div className="flex gap-8">
        <Tooltip content="Left position" position="left">
          <Button variant="secondary">Left</Button>
        </Tooltip>
        <Tooltip content="Right position" position="right">
          <Button variant="secondary">Right</Button>
        </Tooltip>
      </div>
      <Tooltip content="Bottom position" position="bottom">
        <Button variant="secondary">Bottom</Button>
      </Tooltip>
    </div>
  ),
  parameters: {
    layout: 'padded',
  },
  args: {
    content: 'Tooltip',
    children: <Button variant="secondary">Hover me</Button>,
  },
};
