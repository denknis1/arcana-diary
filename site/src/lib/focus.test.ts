import { describe, expect, it } from 'vitest';
import { trapIndex } from './focus';

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
