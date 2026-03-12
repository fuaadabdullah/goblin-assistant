import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import IconButton from '../IconButton';

describe('IconButton', () => {
  const icon = <span data-testid="icon">X</span>;

  it('renders the icon', () => {
    render(<IconButton icon={icon} aria-label="close" />);
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  it('has the aria-label', () => {
    render(<IconButton icon={icon} aria-label="close" />);
    expect(screen.getByRole('button', { name: 'close' })).toBeInTheDocument();
  });

  it('applies variant classes', () => {
    const { container } = render(<IconButton icon={icon} aria-label="x" variant="primary" />);
    expect(container.querySelector('button')?.className).toContain('bg-primary');
  });

  it('applies secondary variant', () => {
    const { container } = render(<IconButton icon={icon} aria-label="x" variant="secondary" />);
    expect(container.querySelector('button')?.className).toContain('bg-surface');
  });

  it('applies danger variant', () => {
    const { container } = render(<IconButton icon={icon} aria-label="x" variant="danger" />);
    expect(container.querySelector('button')?.className).toContain('bg-danger');
  });

  it('applies ghost variant by default', () => {
    const { container } = render(<IconButton icon={icon} aria-label="x" />);
    expect(container.querySelector('button')?.className).toContain('bg-transparent');
  });

  it('applies sm size', () => {
    const { container } = render(<IconButton icon={icon} aria-label="x" size="sm" />);
    expect(container.querySelector('button')?.className).toContain('h-8');
  });

  it('applies md size by default', () => {
    const { container } = render(<IconButton icon={icon} aria-label="x" />);
    expect(container.querySelector('button')?.className).toContain('h-10');
  });

  it('applies lg size', () => {
    const { container } = render(<IconButton icon={icon} aria-label="x" size="lg" />);
    expect(container.querySelector('button')?.className).toContain('h-12');
  });

  it('can be disabled', () => {
    render(<IconButton icon={icon} aria-label="x" disabled />);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('calls onClick', () => {
    const fn = jest.fn();
    render(<IconButton icon={icon} aria-label="x" onClick={fn} />);
    fireEvent.click(screen.getByRole('button'));
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('applies custom className', () => {
    const { container } = render(<IconButton icon={icon} aria-label="x" className="my-class" />);
    expect(container.querySelector('button')?.className).toContain('my-class');
  });

  it('forwards ref', () => {
    const ref = React.createRef<HTMLButtonElement>();
    render(<IconButton icon={icon} aria-label="x" ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLButtonElement);
  });
});
