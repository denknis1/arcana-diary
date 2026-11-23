import { describe, expect, it } from 'vitest';
import { allPagePaths, hreflangPair, langOf } from './routes';
import { DEFAULT_IMAGE, SITE_URL, absoluteUrl, alternates } from './seo';

describe('canonical and hreflang (spec stage 6 §3)', () => {
  it('builds absolute addresses on the production domain', () => {
    expect(SITE_URL).toBe('https://arcanadiary.com');
    expect(absoluteUrl('/')).toBe('https://arcanadiary.com/');
    expect(absoluteUrl('/es')).toBe('https://arcanadiary.com/es');
    expect(absoluteUrl('/cards/the-moon.webp')).toBe('https://arcanadiary.com/cards/the-moon.webp');
    expect(DEFAULT_IMAGE).toBe('/cards/the-moon.webp');
  });

  it('gives a paired page en, es and x-default = EN, from either side', () => {
    const both = [
      { hreflang: 'en', href: 'https://arcanadiary.com/yes-no' },
      { hreflang: 'es', href: 'https://arcanadiary.com/es/si-o-no' },
      { hreflang: 'x-default', href: 'https://arcanadiary.com/yes-no' },
    ];
    expect(alternates('/yes-no')).toEqual(both);
    expect(alternates('/es/si-o-no')).toEqual(both);
    expect(alternates('/')[1]).toEqual({ hreflang: 'es', href: 'https://arcanadiary.com/es' });
  });

  it('gives a page without a mutual pair no hreflang', () => {
    expect(alternates('/one-card')).toEqual([]);
    expect(alternates('/yes-no/cards')).toEqual([]);
    expect(alternates('/es/tiradas/3-cartas')).toEqual([]);
    expect(alternates('/diary')).toEqual([]);
  });

  it('rejects a non-canonical path', () => {
    for (const bad of ['yes-no', '/yes-no/', '/yes-no.html', '/es#una-carta', '']) {
      expect(() => absoluteUrl(bad)).toThrow();
    }
  });

  it('keeps every paired page reciprocal and canonical', () => {
    const all = allPagePaths();
    const known = new Set(all.map(absoluteUrl));
    const hrefRe = /^https:\/\/arcanadiary\.com(\/|(\/[a-z0-9-]+)+)$/;
    let paired = 0;
    for (const p of all) {
      const pair = hreflangPair(p);
      if (pair === null) { expect(alternates(p), p).toEqual([]); continue; }
      paired++;
      const set = alternates(p);
      expect(set, p).toEqual(alternates(pair));
      expect(set.map((a) => a.hreflang), p).toEqual(['en', 'es', 'x-default']);
      expect(set.map((a) => a.href), p).toContain(absoluteUrl(p));
      expect(set[2].href, p).toBe(set[0].href);
      expect(langOf(pair), p).not.toBe(langOf(p));
      for (const a of set) {
        expect(a.href, p).toMatch(hrefRe);
        expect(known.has(a.href), `${p} -> ${a.href}`).toBe(true);
      }
    }
    expect(paired).toBe(168);
  });
});
