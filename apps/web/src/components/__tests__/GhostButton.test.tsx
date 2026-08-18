import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { GhostButton } from '../goblin-buttons/GhostButton';

describe('GhostButton', () => {
  it('renders children', () => {
    render(<GhostButton>Ghost</GhostButton>);
    expect(screen.getByRole('button')).toHaveTextContent('Ghost');
  });

  it('has type button by default', () => {
    render(<GhostButton>Click</GhostButton>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<GhostButton onClick={onClick}>Click</GhostButton>);
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('respects disabled prop', () => {
    render(<GhostButton disabled>Click</GhostButton>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('renders with primary variant by default', () => {
    render(<GhostButton>Ghost</GhostButton>);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });
});
