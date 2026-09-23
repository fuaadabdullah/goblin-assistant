import { useCallback, useRef, type KeyboardEvent } from 'react';

/**
 * Wires the WAI-ARIA "automatic activation" keyboard pattern for a tablist:
 * ArrowLeft/ArrowRight/Home/End move focus AND activate the corresponding
 * tab, with roving tabindex (only the active tab is in the natural Tab
 * order). Attach `onKeyDown` to the tablist container and `registerTab(key)`
 * as the ref on each tab button.
 */
export function useTabListKeyboardNav<T extends string>(
  tabs: readonly T[],
  activeTab: T,
  onChange: (tab: T) => void
) {
  const tabRefs = useRef(new Map<T, HTMLButtonElement>());

  const registerTab = useCallback(
    (tab: T) => (el: HTMLButtonElement | null) => {
      if (el) tabRefs.current.set(tab, el);
      else tabRefs.current.delete(tab);
    },
    []
  );

  const onKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>) => {
      const currentIndex = tabs.indexOf(activeTab);
      let nextIndex: number | null = null;

      if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabs.length;
      else if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      else if (event.key === 'Home') nextIndex = 0;
      else if (event.key === 'End') nextIndex = tabs.length - 1;

      if (nextIndex === null) return;
      event.preventDefault();
      const nextTab = tabs[nextIndex]!;
      onChange(nextTab);
      tabRefs.current.get(nextTab)?.focus();
    },
    [tabs, activeTab, onChange]
  );

  return { onKeyDown, registerTab };
}
