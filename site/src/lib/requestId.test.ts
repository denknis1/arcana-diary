import { describe, expect, it } from 'vitest';
import { newRequestId } from './requestId';

const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

describe('newRequestId', () => {
  it('gives a new UUID v4 every time', () => {
    const ids = new Set(Array.from({ length: 50 }, () => newRequestId()));
    expect(ids.size).toBe(50);
    for (const id of ids) expect(id).toMatch(V4);
  });

  it('builds a v4 from random bytes where crypto.randomUUID is missing', () => {
    const source = { getRandomValues: <T extends ArrayBufferView>(a: T) => { (a as unknown as Uint8Array).fill(0xff); return a; } };
    expect(newRequestId(source)).toBe('ffffffff-ffff-4fff-bfff-ffffffffffff');
  });
});
