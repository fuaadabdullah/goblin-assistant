import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Input } from '../input';

describe('Input', () => {
  it('renders input element', () => {
    render(<Input />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('applies className', () => {
    render(<Input className="custom-class" />);
    expect(screen.getByRole('textbox').className).toContain('custom-class');
  });

  it('supports placeholder', () => {
    render(<Input placeholder="Enter text" />);
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument();
  });

  it('supports disabled state', () => {
    render(<Input disabled />);
    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('spreads additional props', () => {
    render(<Input data-testid="test-input" name="account-name" autoComplete="name" />);
    expect(screen.getByTestId('test-input')).toBeInTheDocument();
    expect(screen.getByTestId('test-input')).toHaveAttribute('name', 'account-name');
    expect(screen.getByTestId('test-input')).toHaveAttribute('autocomplete', 'name');
  });

  it('uses browser default text type when type prop is omitted', () => {
    render(<Input />);
    const input = screen.getByRole('textbox') as HTMLInputElement;
    expect(input.type).toBe('text');
  });

  it('supports explicit type overrides', () => {
    render(<Input type="email" aria-label="Email" />);
    expect(screen.getByRole('textbox', { name: 'Email' })).toHaveAttribute('type', 'email');
  });

  it('applies size variants', () => {
    const { rerender } = render(<Input size="sm" aria-label="small input" />);
    expect(screen.getByRole('textbox', { name: 'small input' }).className).toContain('h-8');

    rerender(<Input size="lg" aria-label="large input" />);
    expect(screen.getByRole('textbox', { name: 'large input' }).className).toContain('h-12');
  });

  it('applies state variants', () => {
    const { rerender } = render(<Input state="error" aria-label="error input" />);
    expect(screen.getByRole('textbox', { name: 'error input' }).className).toContain(
      'border-danger'
    );

    rerender(<Input state="success" aria-label="success input" />);
    expect(screen.getByRole('textbox', { name: 'success input' }).className).toContain(
      'border-success'
    );
  });

  it('forwards refs to the input element', () => {
    const ref = React.createRef<HTMLInputElement>();
    render(<Input ref={ref} aria-label="ref target" />);
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
    expect(ref.current).toBe(screen.getByRole('textbox', { name: 'ref target' }));
  });
});
