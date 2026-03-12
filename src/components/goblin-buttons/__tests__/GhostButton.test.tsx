import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

jest.mock('../buttonStyles', () => ({
  getButtonClasses: (_variant: string, extra: string) => `ghost-btn ${extra}`,
}));

import { GhostButton } from '../GhostButton';

describe('GhostButton', () => {
  it('renders children', () => {
    render(<GhostButton>Click Me</GhostButton>);
    expect(screen.getByText('Click Me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const user = userEvent.setup();
    const onClick = jest.fn();
    render(<GhostButton onClick={onClick}>Click</GhostButton>);
    await user.click(screen.getByText('Click'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('does not fire onClick when disabled', async () => {
    const user = userEvent.setup();
    const onClick = jest.fn();
    render(<GhostButton onClick={onClick} disabled>Click</GhostButton>);
    await user.click(screen.getByText('Click'));
    expect(onClick).not.toHaveBeenCalled();
  });

  it('has disabled attribute when disabled', () => {
    render(<GhostButton disabled>Disabled</GhostButton>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('defaults type to button', () => {
    render(<GhostButton>Btn</GhostButton>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
  });

  it('supports type=submit', () => {
    render(<GhostButton type="submit">Submit</GhostButton>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'submit');
  });

  it('applies primary variant classes by default', () => {
    render(<GhostButton>Primary</GhostButton>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('border-primary');
  });

  it('applies accent variant classes', () => {
    render(<GhostButton variant="accent">Accent</GhostButton>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('border-accent');
  });

  it('applies danger variant classes', () => {
    render(<GhostButton variant="danger">Danger</GhostButton>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('border-danger');
  });

  it('applies custom className', () => {
    render(<GhostButton className="my-class">Custom</GhostButton>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('my-class');
  });

  it('passes extra props through', () => {
    render(<GhostButton data-testid="ghost">Test</GhostButton>);
    expect(screen.getByTestId('ghost')).toBeInTheDocument();
  });
});
