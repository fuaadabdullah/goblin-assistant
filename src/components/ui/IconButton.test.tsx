import { describe, it, expect, jest } from '@jest/globals';
import { render, fireEvent } from '@testing-library/react';
import IconButton from './IconButton';

describe('IconButton', () => {
  it('renders with icon and accessible label', () => {
    const { getByRole } = render(<IconButton icon="🔍" aria-label="Search" />);
    const button = getByRole('button', { name: /search/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('🔍');
  });

  it('handles click events', () => {
  const handleClick = jest.fn();
    const { getByRole } = render(
      <IconButton icon="✓" aria-label="Confirm" onClick={handleClick} />
    );

    const button = getByRole('button');
    fireEvent.click(button);

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('can be disabled', () => {
  const handleClick = jest.fn();
    const { getByRole } = render(
      <IconButton icon="✓" aria-label="Confirm" disabled onClick={handleClick} />
    );

    const button = getByRole('button');
    expect(button).toBeDisabled();

    fireEvent.click(button);
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('applies className prop', () => {
    const { getByRole } = render(
      <IconButton icon="⚙️" aria-label="Settings" className="custom-class" />
    );
    const button = getByRole('button');
    expect(button).toHaveClass('custom-class');
  });

  it('requires aria-label for accessibility', () => {
    const { getByRole } = render(<IconButton icon="❌" aria-label="Close dialog" />);
    const button = getByRole('button', { name: /close dialog/i });
    expect(button).toHaveAccessibleName();
  });
});
