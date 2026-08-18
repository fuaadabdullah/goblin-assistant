import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { GoblinButton } from '../goblin-buttons/GoblinButton';

vi.mock('react', async () => {
  const actual = await vi.importActual('react');
  return { ...actual };
});

describe('GoblinButton', () => {
  it('renders children', () => {
    render(<GoblinButton>Click me</GoblinButton>);
    expect(screen.getByRole('button')).toHaveTextContent('Click me');
  });

  it('has type button by default', () => {
    render(<GoblinButton>Click</GoblinButton>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<GoblinButton onClick={onClick}>Click</GoblinButton>);
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('respects disabled prop', () => {
    render(<GoblinButton disabled>Click</GoblinButton>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('applies custom className', () => {
    render(<GoblinButton className="custom-class">Click</GoblinButton>);
    const button = screen.getByRole('button');
    expect(button.className).toContain('custom-class');
  });

  it('spreads additional props', () => {
    render(<GoblinButton data-testid="goblin-btn">Click</GoblinButton>);
    expect(screen.getByTestId('goblin-btn')).toBeInTheDocument();
  });
});
