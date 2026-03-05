import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import Alert from './Alert';

const meta = {
  title: 'UI/Alert',
  component: Alert,
  parameters: {
    layout: 'padded',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['info', 'success', 'warning', 'danger'],
    },
  },
  args: { onDismiss: fn() },
} satisfies Meta<typeof Alert>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Info: Story = {
  args: {
    variant: 'info',
    message: 'This is an informational message.',
  },
};

export const Success: Story = {
  args: {
    variant: 'success',
    message: 'Your changes have been saved successfully!',
  },
};

export const Warning: Story = {
  args: {
    variant: 'warning',
    message: 'Your session will expire in 5 minutes.',
  },
};

export const Danger: Story = {
  args: {
    variant: 'danger',
    message: 'Failed to connect to the server. Please try again.',
  },
};

export const Dismissible: Story = {
  args: {
    variant: 'info',
    message: 'You can dismiss this alert.',
    dismissible: true,
  },
};

export const LongContent: Story = {
  args: {
    variant: 'warning',
    message:
      'This is a much longer alert message that spans multiple lines. It contains important information that users should read carefully. The alert will automatically adjust its height to accommodate the content.',
    dismissible: true,
  },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-col gap-4">
      <Alert variant="info" message="Info: System maintenance scheduled for tonight." />
      <Alert variant="success" message="Success: Your profile has been updated." />
      <Alert variant="warning" message="Warning: Your free trial ends in 3 days." />
      <Alert variant="danger" message="Error: Unable to process payment." />
    </div>
  ),
  args: {
    message: '',
  },
};
