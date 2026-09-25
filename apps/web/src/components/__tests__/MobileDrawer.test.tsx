import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MobileDrawer from '../MobileDrawer';
import { useUIStore } from '../../store/uiStore';

describe('MobileDrawer', () => {
  afterEach(() => {
    act(() => useUIStore.setState({ mobileNavOpen: false }));
    document.body.style.overflow = '';
  });

  it('renders nothing when closed', () => {
    useUIStore.setState({ mobileNavOpen: false });
    render(<MobileDrawer>content</MobileDrawer>);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders as a modal dialog when open', () => {
    useUIStore.setState({ mobileNavOpen: true });
    render(<MobileDrawer ariaLabel="Main menu">content</MobileDrawer>);

    const dialog = screen.getByRole('dialog', { name: 'Main menu' });
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
  });

  it('wraps Tab from the last focusable element back to the first', async () => {
    const user = userEvent.setup();
    useUIStore.setState({ mobileNavOpen: true });
    render(
      <MobileDrawer>
        <button>Only focusable child</button>
      </MobileDrawer>
    );

    const closeButton = screen.getByRole('button', { name: 'Close menu' });
    const childButton = screen.getByRole('button', { name: 'Only focusable child' });

    // childButton is the last focusable element in the panel; tabbing
    // forward from it must wrap back to the first (closeButton) instead of
    // escaping to whatever follows the drawer in the DOM.
    childButton.focus();
    await user.tab();
    expect(closeButton).toHaveFocus();
  });

  it('wraps Shift+Tab from the first focusable element back to the last', async () => {
    const user = userEvent.setup();
    useUIStore.setState({ mobileNavOpen: true });
    render(
      <MobileDrawer>
        <button>Only focusable child</button>
      </MobileDrawer>
    );

    const closeButton = screen.getByRole('button', { name: 'Close menu' });
    const childButton = screen.getByRole('button', { name: 'Only focusable child' });

    closeButton.focus();
    await user.tab({ shift: true });
    expect(childButton).toHaveFocus();
  });

  it('closes on Escape', async () => {
    const user = userEvent.setup();
    useUIStore.setState({ mobileNavOpen: true });
    render(<MobileDrawer>content</MobileDrawer>);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    await user.keyboard('{Escape}');

    expect(useUIStore.getState().mobileNavOpen).toBe(false);
  });

  it('closes when the close button is clicked', async () => {
    const user = userEvent.setup();
    useUIStore.setState({ mobileNavOpen: true });
    render(<MobileDrawer>content</MobileDrawer>);

    await user.click(screen.getByRole('button', { name: 'Close menu' }));

    expect(useUIStore.getState().mobileNavOpen).toBe(false);
  });
});
