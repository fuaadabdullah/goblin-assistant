import type { Meta, StoryObj } from '@storybook/react';
import Grid from './Grid';

const meta = {
  title: 'UI/Grid',
  component: Grid,
  parameters: {
    layout: 'padded',
  },
  tags: ['autodocs'],
  argTypes: {
    gap: {
      control: 'select',
      options: ['sm', 'md', 'lg'],
    },
  },
} satisfies Meta<typeof Grid>;

export default meta;
type Story = StoryObj<typeof meta>;

const ExampleCard = ({ num }: { num: number }) => (
  <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 text-center">
    <div className="text-2xl font-bold text-blue-400">Card {num}</div>
    <p className="text-sm text-gray-400 mt-2">Example content</p>
  </div>
);

export const Default: Story = {
  args: {
    children: (
      <>
        <ExampleCard num={1} />
        <ExampleCard num={2} />
        <ExampleCard num={3} />
        <ExampleCard num={4} />
      </>
    ),
  },
};

export const SmallGap: Story = {
  args: {
    gap: 'sm',
    children: (
      <>
        <ExampleCard num={1} />
        <ExampleCard num={2} />
        <ExampleCard num={3} />
        <ExampleCard num={4} />
      </>
    ),
  },
};

export const LargeGap: Story = {
  args: {
    gap: 'lg',
    children: (
      <>
        <ExampleCard num={1} />
        <ExampleCard num={2} />
        <ExampleCard num={3} />
        <ExampleCard num={4} />
      </>
    ),
  },
};

export const AutoFitDisabled: Story = {
  args: {
    autoFit: false,
    children: (
      <>
        <ExampleCard num={1} />
        <ExampleCard num={2} />
        <ExampleCard num={3} />
        <ExampleCard num={4} />
        <ExampleCard num={5} />
        <ExampleCard num={6} />
      </>
    ),
  },
};

export const ManyItems: Story = {
  args: {
    children: Array.from({ length: 12 }, (_, i) => <ExampleCard key={i} num={i + 1} />),
  },
};

export const ResponsiveLayout: Story = {
  render: () => (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold text-gray-200 mb-4">Auto-fit (default)</h3>
        <Grid>
          {Array.from({ length: 6 }, (_, i) => (
            <ExampleCard key={i} num={i + 1} />
          ))}
        </Grid>
      </div>
      <div>
        <h3 className="text-lg font-semibold text-gray-200 mb-4">Fixed columns</h3>
        <Grid autoFit={false}>
          {Array.from({ length: 6 }, (_, i) => (
            <ExampleCard key={i} num={i + 1} />
          ))}
        </Grid>
      </div>
    </div>
  ),
  args: {
    children: <ExampleCard num={1} />,
  },
};
