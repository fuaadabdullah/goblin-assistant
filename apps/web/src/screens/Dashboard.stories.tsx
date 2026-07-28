import type { Meta, StoryObj } from '@storybook/react';
import DashboardContent from './Dashboard';

const meta = {
  title: 'Screens/Dashboard',
  component: DashboardContent,
  parameters: {
    layout: 'fullscreen',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof DashboardContent>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  name: 'Loaded',
  parameters: {
    chromatic: { disable: false },
  },
};
