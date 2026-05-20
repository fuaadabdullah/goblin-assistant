import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

jest.mock('../../theme/theme', () => ({
  applyThemePreset: jest.fn(),
}));

import ThemePreview from '../ThemePreview';
import { applyThemePreset } from '../../theme/theme';

const mockApply = applyThemePreset as jest.Mock;

describe('ThemePreview', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Storage.prototype.getItem = jest.fn(() => null);
  });

  it('renders section heading', () => {
    render(<ThemePreview />);
    expect(screen.getByText('Swap palettes instantly')).toBeInTheDocument();
  });

  it('renders all three theme presets', () => {
    render(<ThemePreview />);
    expect(screen.getAllByText('Goblin Default').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Nocturne Violet').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Ember Blaze').length).toBeGreaterThanOrEqual(1);
  });

  it('applies default theme on mount', () => {
    render(<ThemePreview />);
    expect(mockApply).toHaveBeenCalledWith('default');
  });

  it('applies stored theme from localStorage', () => {
    Storage.prototype.getItem = jest.fn(() => 'nocturne');
    render(<ThemePreview />);
    expect(mockApply).toHaveBeenCalledWith('nocturne');
  });

  it('switches theme when button clicked', () => {
    render(<ThemePreview />);
    const buttons = screen.getAllByRole('button');
    const emberBtn = buttons.find(b => b.textContent === 'Ember Blaze');
    fireEvent.click(emberBtn!);
    expect(mockApply).toHaveBeenCalledWith('ember');
  });

  it('shows descriptions for each preset', () => {
    render(<ThemePreview />);
    expect(screen.getByText('Original neon green + magenta stack')).toBeInTheDocument();
    expect(screen.getByText('Deep indigo surfaces with electric cyan accents')).toBeInTheDocument();
    expect(screen.getByText('Warm amber primary with teal highlights')).toBeInTheDocument();
  });

  it('renders color swatches for each preset', () => {
    const { container } = render(<ThemePreview />);
    // 3 presets × 3 colors = 9 swatches
    const swatches = container.querySelectorAll('[style*="background-color"]');
    expect(swatches.length).toBe(9);
  });

  it('highlights active theme button', () => {
    render(<ThemePreview />);
    const defaultBtn = screen.getAllByRole('button').find(b => b.textContent === 'Goblin Default');
    expect(defaultBtn?.className).toContain('border-primary');
  });
});
