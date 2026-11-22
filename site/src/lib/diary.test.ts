import { describe, expect, it } from 'vitest';
import { entryHref, entryParam } from './diary';

describe('diary rules', () => {
  it('opens an entry only for a real reading id', () => {
    expect(entryParam('?r=2B3C4D5E-0000-4000-8000-000000000001')).toBe('2b3c4d5e-0000-4000-8000-000000000001');
    expect(entryParam('?r=../account')).toBeNull();
    expect(entryParam('')).toBeNull();
    expect(entryHref('es', 'abc')).toBe('/es/diario?r=abc');
  });
});
