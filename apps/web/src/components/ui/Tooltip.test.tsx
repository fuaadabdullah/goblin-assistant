import { describe, it, expect } from 'vitest';
import { render, waitFor, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Tooltip from './Tooltip';

describe('Tooltip', () => {
  it('renders trigger element', () => {
    render(
      <Tooltip content="Tooltip text">
        <button>Hover me</button>
      </Tooltip>
    );

    expect(screen.getByText('Hover me')).toBeInTheDocument();
  });

  it('shows tooltip on hover', async () => {
    const user = userEvent.setup();
    render(
      <Tooltip content="Helpful information">
        <button>Hover me</button>
      </Tooltip>
    );

    const trigger = screen.getByText('Hover me');
    await user.hover(trigger);

    await waitFor(() => {
      const tooltip = screen.getByRole('tooltip');
      expect(tooltip).toBeInTheDocument();
      expect(tooltip).toHaveTextContent('Helpful information');
    });
  });

  it('hides tooltip on mouse leave', async () => {
    const user = userEvent.setup();
    render(
      <Tooltip content="Helpful information">
        <button>Hover me</button>
      </Tooltip>
    );

    const trigger = screen.getByText('Hover me');
    await user.hover(trigger);

    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).toBeInTheDocument();
    });

    await user.unhover(trigger);

    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    });
  });

  it('shows tooltip on focus', async () => {
    const user = userEvent.setup();
    render(
      <Tooltip content="Keyboard accessible">
        <button>Focus me</button>
      </Tooltip>
    );

    const trigger = screen.getByText('Focus me');
    await user.tab(); // focus the first focusable element

    await waitFor(() => {
      const tooltip = screen.getByRole('tooltip');
      expect(tooltip).toBeInTheDocument();
    });
  });

  it('hides tooltip on blur', async () => {
    const user = userEvent.setup();
    render(
      <Tooltip content="Keyboard accessible">
        <button>Focus me</button>
      </Tooltip>
    );

    const trigger = screen.getByText('Focus me');
    await user.tab();

    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).toBeInTheDocument();
    });

    await user.tab(); // move focus away

    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    });
  });

  it('applies different positions via data-side', async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <Tooltip content="Top tooltip" position="top">
        <button>Hover</button>
      </Tooltip>
    );

    const trigger = screen.getByText('Hover');
    await user.hover(trigger);

    await waitFor(() => {
      const tooltip = screen.queryByRole('tooltip');
      expect(tooltip).toBeTruthy();
      expect(tooltip).toHaveAttribute('data-side', 'top');
    });

    await user.unhover(trigger);

    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).toBeNull();
    });

    rerender(
      <Tooltip content="Bottom tooltip" position="bottom">
        <button>Hover</button>
      </Tooltip>
    );

    await user.hover(trigger);

    await waitFor(() => {
      const tooltip = screen.queryByRole('tooltip');
      expect(tooltip).toBeTruthy();
      expect(tooltip).toHaveAttribute('data-side', 'bottom');
    });
  });

  it('has proper ARIA attributes', async () => {
    const user = userEvent.setup();
    render(
      <Tooltip content="Accessible tooltip">
        <button>Hover me</button>
      </Tooltip>
    );

    const button = screen.getByText('Hover me');
    await user.hover(button);

    await waitFor(() => {
      const tooltip = screen.getByRole('tooltip');
      expect(tooltip).toHaveAttribute('role', 'tooltip');

      // Radix links the trigger to the tooltip via aria-describedby
      const describedBy = button.getAttribute('aria-describedby');
      expect(describedBy).toBeTruthy();
      expect(tooltip).toHaveAttribute('id', describedBy);
    });
  });

  it('delays showing tooltip', async () => {
    const user = userEvent.setup();
    render(
      <Tooltip content="Delayed tooltip" delay={100}>
        <button>Hover me</button>
      </Tooltip>
    );

    const trigger = screen.getByText('Hover me');
    await user.hover(trigger);

    // Should not appear immediately
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

    // Wait for delay + animation
    await waitFor(
      () => {
        expect(screen.queryByRole('tooltip')).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });
});