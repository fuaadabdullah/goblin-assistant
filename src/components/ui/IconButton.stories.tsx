import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { Home, Settings, Trash2, Menu, X, Plus, Search } from 'lucide-react';
import IconButton from './IconButton';

const meta = {
  title: 'UI/IconButton',
  component: IconButton,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'danger', 'ghost'],
    },
    size: {
      control: 'select',
      options: ['sm', 'md', 'lg'],
    },
  },
  args: { onClick: fn() },
} satisfies Meta<typeof IconButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: {
    variant: 'primary',
    icon: <Home />,
    'aria-label': 'Go to home',
  },
};

export const Secondary: Story = {
  args: {
    variant: 'secondary',
    icon: <Settings />,
    'aria-label': 'Settings',
  },
};

export const Danger: Story = {
  args: {
    variant: 'danger',
    icon: <Trash2 />,
    'aria-label': 'Delete',
  },
};

export const Ghost: Story = {
  args: {
    variant: 'ghost',
    icon: <Menu />,
    'aria-label': 'Menu',
  },
};

export const Small: Story = {
  args: {
    size: 'sm',
    icon: <X />,
    'aria-label': 'Close',
  },
};

export const Large: Story = {
  args: {
    size: 'lg',
    icon: <Plus />,
    'aria-label': 'Add item',
  },
};

export const Disabled: Story = {
  args: {
    icon: <Settings />,
    'aria-label': 'Settings',
    disabled: true,
  },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex gap-4">
      <IconButton variant="primary" icon={<Home />} aria-label="Home" />
      <IconButton variant="secondary" icon={<Settings />} aria-label="Settings" />
      <IconButton variant="danger" icon={<Trash2 />} aria-label="Delete" />
      <IconButton variant="ghost" icon={<Menu />} aria-label="Menu" />
    </div>
  ),
  args: {
    icon: <Home />,
    'aria-label': 'Home',
  },
};

export const AllSizes: Story = {
  render: () => (
    <div className="flex gap-4 items-center">
      <IconButton size="sm" icon={<Search />} aria-label="Search (small)" />
      <IconButton size="md" icon={<Search />} aria-label="Search (medium)" />
      <IconButton size="lg" icon={<Search />} aria-label="Search (large)" />
    </div>
  ),
  args: {
    icon: <Search />,
    'aria-label': 'Search',
  },
};

export const Toolbar: Story = {
  render: () => (
    <div className="flex gap-2 bg-gray-900 p-2 rounded-lg">
      <IconButton variant="ghost" icon={<Home />} aria-label="Home" />
      <IconButton variant="ghost" icon={<Settings />} aria-label="Settings" />
      <IconButton variant="ghost" icon={<Search />} aria-label="Search" />
      <div className="border-l border-gray-700 mx-2" />
      <IconButton variant="danger" icon={<Trash2 />} aria-label="Delete" />
    </div>
  ),
  args: {
    icon: <Home />,
    'aria-label': 'Home',
  },
};
