/**
 * Button stories — manually typed (Storybook isn't a runtime dep on @goblin/ui).
 * The apps/web Storybook consumes these files via the @storybook/nextjs-vite
 * framework, which provides the actual Meta/StoryObj types at story-load time.
 */
import Button from './index';

const meta = {
  title: 'Foundations/Button',
  component: Button,
  tags: ['autodocs'],
};

export default meta;

export const Primary = { args: { variant: 'primary', children: 'Primary' } };
export const Secondary = { args: { variant: 'secondary', children: 'Secondary' } };
export const Danger = { args: { variant: 'danger', children: 'Delete' } };
export const Success = { args: { variant: 'success', children: 'Confirm' } };
export const Ghost = { args: { variant: 'ghost', children: 'Cancel' } };

export const Small = { args: { size: 'sm', children: 'Small' } };
export const Medium = { args: { size: 'md', children: 'Medium' } };
export const Large = { args: { size: 'lg', children: 'Large' } };

export const Loading = { args: { loading: true, children: 'Saving' } };
export const Disabled = { args: { disabled: true, children: 'Disabled' } };
export const FullWidth = { args: { fullWidth: true, children: 'Full width' } };
