import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('../buttonStyles', () => ({
  getButtonClasses: (variant: string, className: string) => `btn-${variant} ${className}`,
}));

import { GoblinButton } from '../GoblinButton';

describe('GoblinButton', () => {
  it('renders children', () => {
    render(<GoblinButton>Click me</GoblinButton>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('has type button by default', () => {
    render(<GoblinButton>Ok</GoblinButton>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
  });

  it('accepts type submit', () => {
    render(<GoblinButton type="submit">Go</GoblinButton>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'submit');
  });

  it('calls onClick', () => {
    const fn = jest.fn();
    render(<GoblinButton onClick={fn}>Go</GoblinButton>);
    fireEvent.click(screen.getByRole('button'));
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('can be disabled', () => {
    render(<GoblinButton disabled>No</GoblinButton>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('applies primary variant class', () => {
    const { container } = render(<GoblinButton>Go</GoblinButton>);
    expect(container.querySelector('button')?.className).toContain('btn-primary');
  });

  it('applies custom className', () => {
    const { container } = render(<GoblinButton className="extra">Go</GoblinButton>);
    expect(container.querySelector('button')?.className).toContain('extra');
  });

  it('spreads additional props', () => {
    render(<GoblinButton data-testid="gb">Go</GoblinButton>);
    expect(screen.getByTestId('gb')).toBeInTheDocument();
  });
});
