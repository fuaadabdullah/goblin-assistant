import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Label } from '../Label';

describe('Label', () => {
  it('renders text', () => {
    render(<Label>Name</Label>);
    expect(screen.getByText('Name')).toBeInTheDocument();
  });

  it('applies className', () => {
    render(<Label className="custom-class">Label</Label>);
    expect(screen.getByText('Label').className).toContain('custom-class');
  });

  it('supports htmlFor attribute', () => {
    render(<Label htmlFor="name">Name</Label>);
    expect(screen.getByText('Name')).toHaveAttribute('for', 'name');
  });
});