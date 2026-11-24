import { describe, expect, it } from 'vitest';
import { allPagePaths, hreflangPair, langOf } from './routes';
import { DEFAULT_IMAGE, SITE_URL, absoluteUrl, alternates, defaultImage } from './seo';
import { hiddenPaths } from './textPages';

describe('canonical and hreflang (spec stage 6 §3)', () => {
  it('builds absolute addresses on the production domain', () => {
    expect(SITE_URL).toBe('https://arcanadiary.com');
    expect(absoluteUrl('/')).toBe('https://arcanadiary.com/');
    expect(absoluteUrl('/es')).toBe('https://arcanadiary.com/es');
    expect(absoluteUrl('/cards/the-moon.webp')).toBe('https://arcanadiary.com/cards/the-moon.webp');
    expect(DEFAULT_IMAGE).toBe('/og/og-en.jpg');
    expect(defaultImage('es')).toBe('/og/og-es.jpg');
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

  it('gives no hreflang to a hidden page or to the pair of one (a pair only when both sides are indexable)', () => {
    expect(alternates('/about', new Set(['/about']))).toEqual([]);
    expect(alternates('/es/sobre-nosotros', new Set(['/about']))).toEqual([]);
    expect(alternates('/how-readings-work').map((a) => a.href)).toEqual(['https://arcanadiary.com/how-readings-work',
      'https://arcanadiary.com/es/como-funcionan-las-lecturas', 'https://arcanadiary.com/how-readings-work']);
    expect(alternates('/how-readings-work', new Set(['/es/como-funcionan-las-lecturas']))).toEqual([]);
    expect(alternates('/es/como-funcionan-las-lecturas', new Set(['/es/como-funcionan-las-lecturas']))).toEqual([]);
  });

  it('pairs the eight newly opened service pages reciprocally', () => {
    const pairs = [['/about', '/es/sobre-nosotros'], ['/contact', '/es/contacto'], ['/privacy', '/es/privacidad'],
      ['/terms', '/es/terminos']];
    for (const [en, es] of pairs) {
      expect(hreflangPair(en)).toBe(es);
      expect(alternates(en), en).toEqual([{ hreflang: 'en', href: absoluteUrl(en) }, { hreflang: 'es', href: absoluteUrl(es) },
        { hreflang: 'x-default', href: absoluteUrl(en) }]);
      expect(alternates(es), es).toEqual(alternates(en));
    }
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
    const hidden = hiddenPaths();
    let paired = 0;
    for (const p of all) {
      const pair = hreflangPair(p);
      if (pair === null || hidden.has(p) || hidden.has(pair)) { expect(alternates(p), p).toEqual([]); continue; }
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
    expect(paired).toBe(168 + 2 + 8); // + how-readings-work pair + the four operator pairs (both sides)
  });
});
