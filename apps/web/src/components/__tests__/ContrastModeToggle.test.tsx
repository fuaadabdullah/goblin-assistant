import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

jest.mock('../../hooks/useContrastMode', () => ({
  useContrastMode: jest.fn(() => ({ mode: 'dark', toggleMode: jest.fn() })),
}));
jest.mock('lucide-react', () => ({
  Contrast: (props: Record<string, unknown>) => <span data-testid="icon-contrast" {...props} />,
  Moon: (props: Record<string, unknown>) => <span data-testid="icon-moon" {...props} />,
  Sun: (props: Record<string, unknown>) => <span data-testid="icon-sun" {...props} />,
}));

import ContrastModeToggle from '../ContrastModeToggle';
import { useContrastMode } from '../../hooks/useContrastMode';

const mockUseContrastMode = useContrastMode as jest.Mock;

describe('ContrastModeToggle', () => {
  beforeEach(() => {
    mockUseContrastMode.mockReturnValue({ mode: 'dark', toggleMode: jest.fn() });
  });

  it('renders button with current theme label', () => {
    render(<ContrastModeToggle />);
    expect(screen.getByRole('button')).toHaveAttribute(
      'aria-label',
      expect.stringContaining('Dark')
    );
  });

  it('displays Dark text', () => {
    render(<ContrastModeToggle />);
    expect(screen.getByText('Dark')).toBeInTheDocument();
  });

  it('displays Light text when mode is light', () => {
    mockUseContrastMode.mockReturnValue({ mode: 'light', toggleMode: jest.fn() });
    render(<ContrastModeToggle />);
    expect(screen.getByText('Light')).toBeInTheDocument();
  });

  it('displays High Contrast text when mode is high', () => {
    mockUseContrastMode.mockReturnValue({ mode: 'high', toggleMode: jest.fn() });
    render(<ContrastModeToggle />);
    expect(screen.getByText('High Contrast')).toBeInTheDocument();
  });

  it('calls toggleMode on click', () => {
    const toggleMode = jest.fn();
    mockUseContrastMode.mockReturnValue({ mode: 'dark', toggleMode });
    render(<ContrastModeToggle />);
    fireEvent.click(screen.getByRole('button'));
    expect(toggleMode).toHaveBeenCalledTimes(1);
  });

  it('renders current mode icon', () => {
    render(<ContrastModeToggle />);
    expect(screen.getByTestId('icon-moon')).toBeInTheDocument();
  });

  it('has correct title attribute', () => {
    render(<ContrastModeToggle />);
    expect(screen.getByRole('button')).toHaveAttribute('title', 'Theme: Dark');
  });

  it('renders different icon for light mode', () => {
    mockUseContrastMode.mockReturnValue({ mode: 'light', toggleMode: jest.fn() });
    render(<ContrastModeToggle />);
    expect(screen.getByTestId('icon-sun')).toBeInTheDocument();
  });
});
