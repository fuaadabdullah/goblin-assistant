import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useTabListKeyboardNav } from '../useTabListKeyboardNav';

const TABS = ['a', 'b', 'c'] as const;
type Tab = (typeof TABS)[number];

function TestTabList({ initial = 'a' as Tab }: { initial?: Tab }) {
  const [active, setActive] = useState<Tab>(initial);
  const { onKeyDown, registerTab } = useTabListKeyboardNav(TABS, active, setActive);

  return (
    <div role="tablist" onKeyDown={onKeyDown}>
      {TABS.map((tab) => (
        <button
          key={tab}
          role="tab"
          aria-selected={active === tab}
          tabIndex={active === tab ? 0 : -1}
          ref={registerTab(tab)}
        >
          Tab {tab}
        </button>
      ))}
    </div>
  );
}

describe('useTabListKeyboardNav', () => {
  it('moves to and activates the next tab on ArrowRight', async () => {
    const user = userEvent.setup();
    render(<TestTabList />);

    screen.getByRole('tab', { name: 'Tab a' }).focus();
    await user.keyboard('{ArrowRight}');

    const tabB = screen.getByRole('tab', { name: 'Tab b' });
    expect(tabB).toHaveFocus();
    expect(tabB).toHaveAttribute('aria-selected', 'true');
  });

  it('moves to and activates the previous tab on ArrowLeft', async () => {
    const user = userEvent.setup();
    render(<TestTabList initial="b" />);

    screen.getByRole('tab', { name: 'Tab b' }).focus();
    await user.keyboard('{ArrowLeft}');

    const tabA = screen.getByRole('tab', { name: 'Tab a' });
    expect(tabA).toHaveFocus();
    expect(tabA).toHaveAttribute('aria-selected', 'true');
  });

  it('wraps from the last tab to the first on ArrowRight', async () => {
    const user = userEvent.setup();
    render(<TestTabList initial="c" />);

    screen.getByRole('tab', { name: 'Tab c' }).focus();
    await user.keyboard('{ArrowRight}');

    expect(screen.getByRole('tab', { name: 'Tab a' })).toHaveFocus();
  });

  it('wraps from the first tab to the last on ArrowLeft', async () => {
    const user = userEvent.setup();
    render(<TestTabList initial="a" />);

    screen.getByRole('tab', { name: 'Tab a' }).focus();
    await user.keyboard('{ArrowLeft}');

    expect(screen.getByRole('tab', { name: 'Tab c' })).toHaveFocus();
  });

  it('jumps to the first tab on Home and the last on End', async () => {
    const user = userEvent.setup();
    render(<TestTabList initial="b" />);

    screen.getByRole('tab', { name: 'Tab b' }).focus();
    await user.keyboard('{Home}');
    expect(screen.getByRole('tab', { name: 'Tab a' })).toHaveFocus();

    await user.keyboard('{End}');
    expect(screen.getByRole('tab', { name: 'Tab c' })).toHaveFocus();
  });

  it('only keeps the active tab in the natural Tab order (roving tabindex)', () => {
    render(<TestTabList initial="b" />);

    expect(screen.getByRole('tab', { name: 'Tab a' })).toHaveAttribute('tabindex', '-1');
    expect(screen.getByRole('tab', { name: 'Tab b' })).toHaveAttribute('tabindex', '0');
    expect(screen.getByRole('tab', { name: 'Tab c' })).toHaveAttribute('tabindex', '-1');
  });
});
