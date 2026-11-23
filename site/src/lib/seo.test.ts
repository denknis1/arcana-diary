import { describe, expect, it } from 'vitest';
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

  it('gives a page without a mutual pair only its own link', () => {
    expect(alternates('/one-card')).toEqual([{ hreflang: 'en', href: 'https://arcanadiary.com/one-card' }]);
    expect(alternates('/es/tiradas/3-cartas')).toEqual([
      { hreflang: 'es', href: 'https://arcanadiary.com/es/tiradas/3-cartas' }]);
  });
});
