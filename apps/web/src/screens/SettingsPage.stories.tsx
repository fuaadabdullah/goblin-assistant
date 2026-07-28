import type { Meta, StoryObj } from '@storybook/react';
import SettingsPageContent from './SettingsPage';

const meta = {
  title: 'Screens/Settings',
  component: SettingsPageContent,
  parameters: {
    layout: 'fullscreen',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof SettingsPageContent>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  name: 'Loaded',
  parameters: {
    chromatic: { disable: false },
  },
};
