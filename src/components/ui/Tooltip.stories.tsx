import type { Meta, StoryObj } from '@storybook/react';
import { HelpCircle } from 'lucide-react';
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
    children: <button className="px-4 py-2 bg-blue-600 rounded text-white">Hover me</button>,
  },
};

export const Top: Story = {
  args: {
    content: 'Tooltip appears above',
    position: 'top',
    children: <button className="px-4 py-2 bg-blue-600 rounded text-white">Hover me</button>,
  },
};

export const Bottom: Story = {
  args: {
    content: 'Tooltip appears below',
    position: 'bottom',
    children: <button className="px-4 py-2 bg-blue-600 rounded text-white">Hover me</button>,
  },
};

export const Left: Story = {
  args: {
    content: 'Tooltip appears left',
    position: 'left',
    children: <button className="px-4 py-2 bg-blue-600 rounded text-white">Hover me</button>,
  },
};

export const Right: Story = {
  args: {
    content: 'Tooltip appears right',
    position: 'right',
    children: <button className="px-4 py-2 bg-blue-600 rounded text-white">Hover me</button>,
  },
};

export const WithIcon: Story = {
  args: {
    content: 'Click for more information',
    children: (
      <button className="p-2 text-gray-400 hover:text-gray-200" aria-label="Help">
        <HelpCircle size={20} />
      </button>
    ),
  },
};

export const LongContent: Story = {
  args: {
    content:
      'This tooltip contains a longer message that might span multiple lines. It provides detailed information to help users understand the feature.',
    children: (
      <button className="px-4 py-2 bg-blue-600 rounded text-white">Hover for details</button>
    ),
  },
};

export const AllPositions: Story = {
  render: () => (
    <div className="flex flex-col gap-8 items-center">
      <Tooltip content="Top position" position="top">
        <button className="px-4 py-2 bg-blue-600 rounded text-white">Top</button>
      </Tooltip>
      <div className="flex gap-8">
        <Tooltip content="Left position" position="left">
          <button className="px-4 py-2 bg-blue-600 rounded text-white">Left</button>
        </Tooltip>
        <Tooltip content="Right position" position="right">
          <button className="px-4 py-2 bg-blue-600 rounded text-white">Right</button>
        </Tooltip>
      </div>
      <Tooltip content="Bottom position" position="bottom">
        <button className="px-4 py-2 bg-blue-600 rounded text-white">Bottom</button>
      </Tooltip>
    </div>
  ),
  parameters: {
    layout: 'padded',
  },
  args: {
    content: 'Tooltip',
    children: <button>Hover me</button>,
  },
};
