import { describe, it, expect, jest } from "vitest";
import { render, fireEvent } from '@testing-library/react';
import Button from './Button';

describe('Button', () => {
  test('renders with default variant and size', () => {
    const { getByRole } = render(<Button>Click me</Button>);
    const button = getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-primary');
  });

  test('renders with different variants', () => {
    const { rerender, getByRole } = render(<Button variant="secondary">Secondary</Button>);
    let button = getByRole('button');
    expect(button).toHaveClass('bg-surface-hover');

    rerender(<Button variant="danger">Danger</Button>);
    button = getByRole('button');
    expect(button).toHaveClass('bg-danger');

    rerender(<Button variant="ghost">Ghost</Button>);
    button = getByRole('button');
    expect(button).toHaveClass('bg-transparent');
  });

  test('renders with different sizes', () => {
    const { rerender, getByRole } = render(<Button size="sm">Small</Button>);
    let button = getByRole('button');
    expect(button).toHaveClass('text-sm');

    rerender(<Button size="lg">Large</Button>);
    button = getByRole('button');
    expect(button).toHaveClass('text-base');
  });

  test('handles click events', () => {
  const handleClick = jest.fn();
    const { getByRole } = render(<Button onClick={handleClick}>Click me</Button>);

    const button = getByRole('button');
    fireEvent.click(button);

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  test('renders with icon', () => {
    const { getByRole } = render(<Button icon="🚀">Launch</Button>);
    const button = getByRole('button');
    expect(button).toHaveTextContent('🚀');
    expect(button).toHaveTextContent('Launch');
  });

  test('can be disabled', () => {
  const handleClick = jest.fn();
    const { getByRole } = render(
      <Button onClick={handleClick} disabled>
        Disabled
      </Button>
    );

    const button = getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveClass('disabled:opacity-50'); // Check for disabled class variant

    fireEvent.click(button);
    expect(handleClick).not.toHaveBeenCalled(); // Disabled buttons shouldn't fire clicks
  });

  test('renders with fullWidth', () => {
    const { getByRole } = render(<Button fullWidth>Full Width</Button>);
    const button = getByRole('button');
    expect(button).toHaveClass('w-full');
  });

  test('forwards aria-label', () => {
    const { getByRole } = render(<Button aria-label="Custom label">Button</Button>);
    const button = getByRole('button', { name: /custom label/i });
    expect(button).toBeInTheDocument();
  });
});
