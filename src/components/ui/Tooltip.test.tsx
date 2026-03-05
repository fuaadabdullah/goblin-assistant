import { describe, it, expect } from '@jest/globals';
import { render, fireEvent, waitFor } from '@testing-library/react';
import Tooltip from './Tooltip';

describe('Tooltip', () => {
  it('renders trigger element', () => {
    const { getByText } = render(
      <Tooltip content="Tooltip text">
        <button>Hover me</button>
      </Tooltip>
    );

    expect(getByText('Hover me')).toBeInTheDocument();
  });

  it('shows tooltip on hover', async () => {
    const { getByText, getByRole } = render(
      <Tooltip content="Helpful information">
        <button>Hover me</button>
      </Tooltip>
    );

    const trigger = getByText('Hover me');

    // Hover to show tooltip
    fireEvent.mouseEnter(trigger);

    await waitFor(() => {
      const tooltip = getByRole('tooltip');
      expect(tooltip).toBeInTheDocument();
      expect(tooltip).toHaveTextContent('Helpful information');
    });
  });

  it('hides tooltip on mouse leave', async () => {
    const { getByText, queryByRole } = render(
      <Tooltip content="Helpful information">
        <button>Hover me</button>
      </Tooltip>
    );

    const trigger = getByText('Hover me');

    // Show tooltip
    fireEvent.mouseEnter(trigger);
    await waitFor(() => {
      expect(queryByRole('tooltip')).toBeInTheDocument();
    });

    // Hide tooltip
    fireEvent.mouseLeave(trigger);
    await waitFor(() => {
      expect(queryByRole('tooltip')).not.toBeInTheDocument();
    });
  });

  it('shows tooltip on focus', async () => {
    const { getByText, getByRole } = render(
      <Tooltip content="Keyboard accessible">
        <button>Focus me</button>
      </Tooltip>
    );

    const trigger = getByText('Focus me');

    fireEvent.focus(trigger);

    await waitFor(() => {
      const tooltip = getByRole('tooltip');
      expect(tooltip).toBeInTheDocument();
    });
  });

  it('hides tooltip on blur', async () => {
    const { getByText, queryByRole } = render(
      <Tooltip content="Keyboard accessible">
        <button>Focus me</button>
      </Tooltip>
    );

    const trigger = getByText('Focus me');

    // Show tooltip
    fireEvent.focus(trigger);
    await waitFor(() => {
      expect(queryByRole('tooltip')).toBeInTheDocument();
    });

    // Hide tooltip
    fireEvent.blur(trigger);
    await waitFor(() => {
      expect(queryByRole('tooltip')).not.toBeInTheDocument();
    });
  });

  it('applies different positions', async () => {
    const { getByText, queryByRole, rerender } = render(
      <Tooltip content="Top tooltip" position="top">
        <button>Hover</button>
      </Tooltip>
    );

    fireEvent.mouseEnter(getByText('Hover'));

    await waitFor(() => {
      const tooltip = queryByRole('tooltip');
      expect(tooltip).toBeTruthy();
      expect(tooltip).toHaveClass('bottom-full');
    });

    fireEvent.mouseLeave(getByText('Hover'));

    // Wait for tooltip to hide
    await waitFor(() => {
      expect(queryByRole('tooltip')).toBeNull();
    });

    rerender(
      <Tooltip content="Bottom tooltip" position="bottom">
        <button>Hover</button>
      </Tooltip>
    );

    fireEvent.mouseEnter(getByText('Hover'));

    await waitFor(() => {
      const tooltip = queryByRole('tooltip');
      expect(tooltip).toBeTruthy();
      expect(tooltip).toHaveClass('top-full');
    });
  });

  it('has proper ARIA attributes', async () => {
    const { getByText, getByRole } = render(
      <Tooltip content="Accessible tooltip">
        <button>Hover me</button>
      </Tooltip>
    );

    const button = getByText('Hover me');
    fireEvent.mouseEnter(button);

    await waitFor(() => {
      const tooltip = getByRole('tooltip');
      expect(tooltip).toHaveAttribute('role', 'tooltip');

      const tooltipId = tooltip.getAttribute('id');
      expect(tooltipId).toBeTruthy();

      // aria-describedby is on the wrapper div, not the button
      const wrapper = button.parentElement;
      expect(wrapper).toHaveAttribute('aria-describedby', tooltipId);
    });
  });

  it('delays showing tooltip', async () => {
    const { getByText, queryByRole } = render(
      <Tooltip content="Delayed tooltip" delay={100}>
        <button>Hover me</button>
      </Tooltip>
    );

    const trigger = getByText('Hover me');
    fireEvent.mouseEnter(trigger);

    // Should not appear immediately
    expect(queryByRole('tooltip')).not.toBeInTheDocument();

    // Wait for delay + animation
    await waitFor(
      () => {
        expect(queryByRole('tooltip')).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });
});
