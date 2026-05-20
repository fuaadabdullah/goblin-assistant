import type { Meta, StoryObj } from '@storybook/react';
import { ToastProvider } from '../contexts/ToastContext';
import { ToastItem } from './ToastItem';
import { ToastContainer } from './ToastContainer';
import { useToast } from '../contexts/ToastContext';
import Button from './ui/Button';

const meta = {
  title: 'Components/Toast',
  component: ToastItem,
  tags: ['autodocs'],
} satisfies Meta<typeof ToastItem>;

export default meta;
type Story = StoryObj<typeof meta>;

export const SuccessToast: Story = {
  render: () => (
    <ToastItem
      toast={{ id: '1', type: 'success', title: 'Saved', message: 'Your changes are live.' }}
      onRemove={() => undefined}
    />
  ),
};

function ToastHarness() {
  const { showSuccess, showError } = useToast();

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <Button onClick={() => showSuccess('Action complete', 'Everything finished cleanly.')}>
          Show success
        </Button>
        <Button variant="danger" onClick={() => showError('Action failed', 'Please try again.')}>
          Show error
        </Button>
      </div>
      <ToastContainer />
    </div>
  );
}

export const Container: Story = {
  render: () => (
    <ToastProvider>
      <ToastHarness />
    </ToastProvider>
  ),
};
