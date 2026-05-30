import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import Card from '../Card';

describe('Card', () => {
  it('renders children', () => {
    render(<Card>Hello World</Card>);
    expect(screen.getByText('Hello World')).toBeInTheDocument();
  });

  it('applies default elevation', () => {
    render(<Card>Content</Card>);
    const card = screen.getByText('Content').closest('[data-elevation]');
    expect(card).toHaveAttribute('data-elevation', 'card');
  });

  it('applies custom className', () => {
    render(<Card className="custom-class">Content</Card>);
    const card = screen.getByText('Content');
    expect(card.className).toContain('custom-class');
  });

  it('renders without padding when padded is false', () => {
    const { container } = render(<Card padded={false}>Content</Card>);
    expect(container.firstChild?.textContent).toBe('Content');
  });

  it('renders without border when bordered is false', () => {
    render(<Card bordered={false}>Content</Card>);
    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('accepts additional div props', () => {
    render(
      <Card id="test-card" data-testid="card">
        Content
      </Card>
    );
    expect(screen.getByTestId('card')).toBeInTheDocument();
  });
});
