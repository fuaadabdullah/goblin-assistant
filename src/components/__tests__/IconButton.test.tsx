import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { IconButton } from '../goblin-buttons/IconButton';

describe('IconButton (goblin-buttons)', () => {
  const testLabel = 'Close panel';
  const child = <span data-testid="icon-child">X</span>;

  it('renders children', () => {
    render(<IconButton aria-label={testLabel}>{child}</IconButton>);
    expect(screen.getByTestId('icon-child')).toBeInTheDocument();
  });

  it('renders with aria-label', () => {
    render(<IconButton aria-label={testLabel}>{child}</IconButton>);
    expect(screen.getByRole('button', { name: testLabel })).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = jest.fn();
    render(
      <IconButton aria-label={testLabel} onClick={onClick}>
        {child}
      </IconButton>
    );
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('respects disabled prop', () => {
    render(
      <IconButton aria-label={testLabel} disabled>
        {child}
      </IconButton>
    );
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('applies custom className', () => {
    render(
      <IconButton aria-label={testLabel} className="extra-class">
        {child}
      </IconButton>
    );
    const button = screen.getByRole('button');
    expect(button.className).toContain('extra-class');
  });

  it('defaults to ghost variant styling', () => {
    render(<IconButton aria-label={testLabel}>{child}</IconButton>);
    const button = screen.getByRole('button');
    // icon-ghost returns: p-2 rounded-md hover:bg-surface/50 ...
    expect(button.className).toContain('rounded-md');
    expect(button.className).toContain('duration-150');
  });

  it('applies primary variant classes', () => {
    render(
      <IconButton aria-label={testLabel} variant="primary">
        {child}
      </IconButton>
    );
    const button = screen.getByRole('button');
    // icon-primary returns: p-2 rounded-md hover:bg-primary/15 ...
    expect(button.className).toContain('rounded-md');
    expect(button.className).toContain('duration-150');
  });

  it('applies danger variant classes', () => {
    render(
      <IconButton aria-label={testLabel} variant="danger">
        {child}
      </IconButton>
    );
    const button = screen.getByRole('button');
    // icon-danger returns: p-2 rounded-md hover:bg-danger/15 ...
    expect(button.className).toContain('rounded-md');
    expect(button.className).toContain('duration-150');
  });

  it('spreads additional props', () => {
    render(
      <IconButton aria-label={testLabel} data-testid="custom-btn">
        {child}
      </IconButton>
    );
    expect(screen.getByTestId('custom-btn')).toBeInTheDocument();
  });
});
