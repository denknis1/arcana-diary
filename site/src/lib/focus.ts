// Focus kept inside the night room (00-design.md: focus trapped, Escape closes, focus returns to the draw button).

export const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Where Tab must go so that focus stays inside: the index to focus, or null to let the browser move on.
 * `current` is the index of the focused element among `count` focusables (-1: focus is outside). */
export function trapIndex(count: number, current: number, backwards: boolean): number | null {
  if (count === 0) return null;
  if (current < 0) return backwards ? count - 1 : 0;
  if (backwards && current === 0) return count - 1;
  if (!backwards && current === count - 1) return 0;
  return null;
}

/** Keydown inside a dialog: Escape → onEscape; Tab at the edges wraps around. */
export function handleDialogKey(event: KeyboardEvent, container: HTMLElement, onEscape: () => void): void {
  if (event.key === 'Escape') {
    event.preventDefault();
    onEscape();
    return;
  }
  if (event.key !== 'Tab') return;
  const items = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((el) => el.tabIndex >= 0 && !el.closest('[hidden],[inert]'));
  const target = trapIndex(items.length, items.indexOf(document.activeElement as HTMLElement), event.shiftKey);
  if (target !== null) {
    event.preventDefault();
    items[target].focus();
  }
}
