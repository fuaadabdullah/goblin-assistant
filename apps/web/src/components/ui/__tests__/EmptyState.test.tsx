import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import EmptyState from '../EmptyState';

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(<EmptyState title="No data" description="Nothing to show here." />);
    expect(screen.getByText('No data')).toBeInTheDocument();
    expect(screen.getByText('Nothing to show here.')).toBeInTheDocument();
  });

  it('renders icon container as aria-hidden when icon is provided', () => {
    render(
      <EmptyState title="No data" description="x" icon={<span data-testid="icon-glyph">📦</span>} />
    );
    const iconNode = screen.getByTestId('icon-glyph');
    expect(iconNode).toBeInTheDocument();
    expect(iconNode.parentElement).toHaveAttribute('aria-hidden', 'true');
  });

  it('omits the icon container when icon is absent', () => {
    const { container } = render(<EmptyState title="t" description="d" />);
    expect(container.querySelector('[aria-hidden="true"]')).not.toBeInTheDocument();
  });

  it('renders action button and calls onAction when no href is provided', () => {
    const onAction = jest.fn();
    render(<EmptyState title="t" description="d" actionLabel="Do it" onAction={onAction} />);
    const btn = screen.getByRole('button', { name: 'Do it' });
    fireEvent.click(btn);
    expect(onAction).toHaveBeenCalledTimes(1);
  });

  it('renders a primary link action even when onAction is omitted', () => {
    render(
      <EmptyState
        title="Docs"
        description="Read the docs"
        actionLabel="Open docs"
        actionHref="/docs"
      />
    );
    const link = screen.getByRole('link', { name: 'Open docs' });
    expect(link).toHaveAttribute('href', '/docs');
    expect(screen.queryByRole('button', { name: 'Open docs' })).not.toBeInTheDocument();
  });

  it('renders action as anchor when actionHref is provided', () => {
    const onAction = jest.fn();
    render(
      <EmptyState
        title="t"
        description="d"
        actionLabel="Open docs"
        actionHref="https://example.com"
        onAction={onAction}
      />
    );
    const link = screen.getByRole('link', { name: 'Open docs' });
    expect(link).toHaveAttribute('href', 'https://example.com');
    // Anchor variant ignores onAction
    fireEvent.click(link);
    expect(onAction).not.toHaveBeenCalled();
  });

  it('omits the action when actionLabel is missing', () => {
    render(
      <EmptyState title="t" description="d" onAction={() => undefined} actionHref="/somewhere" />
    );
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('renders secondaryAction alongside primary action', () => {
    render(
      <EmptyState
        title="t"
        description="d"
        actionLabel="Primary"
        onAction={() => undefined}
        secondaryAction={<button>Secondary</button>}
      />
    );
    expect(screen.getByRole('button', { name: 'Primary' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Secondary' })).toBeInTheDocument();
  });

  it('renders secondaryAction even without a primary action', () => {
    render(
      <EmptyState title="t" description="d" secondaryAction={<button>Only secondary</button>} />
    );
    expect(screen.getByRole('button', { name: 'Only secondary' })).toBeInTheDocument();
  });

  it('does not render any interactive action when no action props are provided', () => {
    render(<EmptyState title="t" description="d" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('applies custom className to the card', () => {
    const { container } = render(<EmptyState title="t" description="d" className="custom-empty" />);
    expect(container.querySelector('.custom-empty')).toBeInTheDocument();
  });
});
