import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import PageState from '../PageState';

describe('PageState', () => {
  describe('loading variant', () => {
    it('renders SectionLoadingState with title and description', () => {
      render(
        <PageState
          variant="loading"
          title="Loading providers"
          description="Hang tight, fetching configuration."
        />
      );
      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByText('Loading providers')).toBeInTheDocument();
      expect(screen.getByText('Hang tight, fetching configuration.')).toBeInTheDocument();
    });

    it('uses the title for the status aria-label', () => {
      render(<PageState variant="loading" title="Loading X" description="..." />);
      expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Loading X');
    });

    it('renders provided icon', () => {
      render(
        <PageState
          variant="loading"
          title="Loading"
          description="..."
          icon={<span data-testid="loading-icon">⏳</span>}
        />
      );
      expect(screen.getByTestId('loading-icon')).toBeInTheDocument();
    });
  });

  describe('empty variant', () => {
    it('renders title and description', () => {
      render(
        <PageState
          variant="empty"
          title="Nothing here yet"
          description="Add your first item to get started."
        />
      );
      expect(screen.getByText('Nothing here yet')).toBeInTheDocument();
      expect(screen.getByText('Add your first item to get started.')).toBeInTheDocument();
    });

    it('renders action button and calls onAction', () => {
      const onAction = jest.fn();
      render(
        <PageState
          variant="empty"
          title="Empty"
          description="..."
          actionLabel="Create item"
          onAction={onAction}
        />
      );
      fireEvent.click(screen.getByRole('button', { name: 'Create item' }));
      expect(onAction).toHaveBeenCalledTimes(1);
    });

    it('renders action as link when actionHref is provided', () => {
      render(
        <PageState
          variant="empty"
          title="Empty"
          description="..."
          actionLabel="Go home"
          actionHref="/home"
        />
      );
      const link = screen.getByRole('link', { name: 'Go home' });
      expect(link).toHaveAttribute('href', '/home');
    });

    it('renders secondary action', () => {
      render(
        <PageState
          variant="empty"
          title="Empty"
          description="..."
          secondaryAction={<button>Help</button>}
        />
      );
      expect(screen.getByRole('button', { name: 'Help' })).toBeInTheDocument();
    });

    it('renders icon when provided', () => {
      render(
        <PageState
          variant="empty"
          title="Empty"
          description="..."
          icon={<span data-testid="empty-icon">📭</span>}
        />
      );
      expect(screen.getByTestId('empty-icon')).toBeInTheDocument();
    });
  });

  describe('error variant', () => {
    it('renders title and message', () => {
      render(
        <PageState
          variant="error"
          title="Something broke"
          description="Try again in a moment."
        />
      );
      expect(screen.getByText('Something broke')).toBeInTheDocument();
      expect(screen.getByText('Try again in a moment.')).toBeInTheDocument();
    });

    it('renders retry button when onAction is provided and triggers it', () => {
      const onAction = jest.fn();
      render(
        <PageState
          variant="error"
          title="Boom"
          description="x"
          onAction={onAction}
          retryLabel="Retry now"
        />
      );
      fireEvent.click(screen.getByRole('button', { name: 'Retry now' }));
      expect(onAction).toHaveBeenCalledTimes(1);
    });

    it('falls back to actionLabel when retryLabel is missing', () => {
      const onAction = jest.fn();
      render(
        <PageState
          variant="error"
          title="Boom"
          description="x"
          onAction={onAction}
          actionLabel="Try again"
        />
      );
      expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
    });

    it('omits retry button when no onAction', () => {
      render(<PageState variant="error" title="Boom" description="x" />);
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
  });

  describe('layout', () => {
    it('applies custom className to outer wrapper', () => {
      const { container } = render(
        <PageState
          variant="empty"
          title="t"
          description="d"
          className="custom-page"
        />
      );
      expect((container.firstChild as HTMLElement).className).toContain('custom-page');
    });

    it('renders min-h-screen background container', () => {
      const { container } = render(
        <PageState variant="empty" title="t" description="d" />
      );
      expect((container.firstChild as HTMLElement).className).toContain('min-h-screen');
    });
  });
});
