import { describe, expect, it } from 'vitest';
import { handleDialogKey, trapIndex } from './focus';

describe('trapIndex', () => {
  it('wraps Tab from the last element to the first and Shift+Tab back', () => {
    expect(trapIndex(4, 3, false)).toBe(0);
    expect(trapIndex(4, 0, true)).toBe(3);
  });

  it('lets the browser move inside the dialog', () => {
    expect(trapIndex(4, 1, false)).toBeNull();
    expect(trapIndex(4, 2, true)).toBeNull();
  });

  it('pulls focus back in from outside, and does nothing without focusables', () => {
    expect(trapIndex(3, -1, false)).toBe(0);
    expect(trapIndex(3, -1, true)).toBe(2);
    expect(trapIndex(0, -1, false)).toBeNull();
  });
});

describe('handleDialogKey', () => {
  interface Fake { tabIndex: number; hiddenAncestor: boolean; focused: boolean; closest(sel: string): unknown; focus(): void }
  const fake = (tabIndex: number, hiddenAncestor = false): Fake => ({
    tabIndex, hiddenAncestor, focused: false,
    closest(sel: string) { return sel === '[hidden],[inert]' && this.hiddenAncestor ? {} : null; },
    focus() { this.focused = true; },
  });

  it('skips tabindex=-1 and hidden/inert elements when wrapping', () => {
    const first = fake(0), last = fake(0), negative = fake(-1), hidden = fake(0, true);
    const items = [first, negative, last, hidden];
    const container = { querySelectorAll: () => items } as unknown as HTMLElement;
    (globalThis as { document?: unknown }).document = { activeElement: last };
    let prevented = false;
    handleDialogKey({ key: 'Tab', shiftKey: false, preventDefault: () => { prevented = true; } } as KeyboardEvent, container, () => {});
    delete (globalThis as { document?: unknown }).document;
    expect(prevented).toBe(true);
    expect(first.focused).toBe(true);
    expect(hidden.focused).toBe(false);
  });
});
