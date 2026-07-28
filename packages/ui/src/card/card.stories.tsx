/**
 * Card stories — manually typed (Storybook isn't a runtime dep on @goblin/ui).
 */
import * as React from 'react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from './index';

const meta = {
  title: 'Foundations/Card',
  component: Card,
  tags: ['autodocs'],
};

export default meta;

const renderCard = (args: Record<string, unknown> = {}): React.ReactNode => (
  <Card {...args}>
    <CardHeader>
      <CardTitle>Card title</CardTitle>
      <CardDescription>Supporting copy goes here.</CardDescription>
    </CardHeader>
    <CardContent>
      <p>Body content for the card. Use sparingly — the Card is a layout primitive.</p>
    </CardContent>
    <CardFooter>
      <span>Footer</span>
    </CardFooter>
  </Card>
);

export const Default = { render: (): React.ReactNode => renderCard() };
export const Interactive = { args: { variant: 'interactive' }, render: (): React.ReactNode => renderCard({ variant: 'interactive' }) };
export const Elevated = { args: { variant: 'elevated' }, render: (): React.ReactNode => renderCard({ variant: 'elevated' }) };
export const NoPadding = { args: { padding: 'none' }, render: (): React.ReactNode => renderCard({ padding: 'none' }) };
