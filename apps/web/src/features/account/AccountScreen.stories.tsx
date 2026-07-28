import type { Meta, StoryObj } from '@storybook/react';
import AccountScreen from './AccountScreen';

const meta = {
  title: 'Screens/Account',
  component: AccountScreen,
  parameters: {
    layout: 'fullscreen',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof AccountScreen>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  name: 'Loaded',
  parameters: {
    chromatic: { disable: false },
  },
};
