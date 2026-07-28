import type { Meta, StoryObj } from '@storybook/react';
import { Card, CardContent } from '@goblin/ui';
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

const ExampleCard = (props: { num: number }) => {
  const num = props.num;

  return (
    <Card>
      <CardContent className="p-4 text-center">
        <div className="text-2xl font-bold text-primary">Card {num}</div>
        <p className="mt-2 text-sm text-text-muted">Example content</p>
      </CardContent>
    </Card>
  );
};

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
        <h3 className="mb-4 text-lg font-semibold text-text-primary">Auto-fit (default)</h3>
        <Grid>
          {Array.from({ length: 6 }, (_, i) => (
            <ExampleCard key={i} num={i + 1} />
          ))}
        </Grid>
      </div>
      <div>
        <h3 className="mb-4 text-lg font-semibold text-text-primary">Fixed columns</h3>
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
