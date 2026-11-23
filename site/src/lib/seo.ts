// Canonical address and hreflang of a page (spec stage 6 §3): canonical https://arcanadiary.com{path}; en, es and
// x-default = EN for a page whose pair in pairs.json points back at it; a page without such a pair gets only its own
// link.
import { hreflangPair, langOf } from './routes';

export const SITE_URL = 'https://arcanadiary.com';
/** Share picture of a page without its own card scan (no 1200 × 630 picture exists yet). */
export const DEFAULT_IMAGE = '/cards/the-moon.webp';

export interface Alternate {
  hreflang: 'en' | 'es' | 'x-default';
  href: string;
}

export function absoluteUrl(path: string): string {
  return path === '/' ? `${SITE_URL}/` : `${SITE_URL}${path}`;
}

export function alternates(path: string): Alternate[] {
  const lang = langOf(path);
  const pair = hreflangPair(path);
  if (pair === null) return [{ hreflang: lang, href: absoluteUrl(path) }];
  const en = lang === 'en' ? path : pair;
  const es = lang === 'es' ? path : pair;
  return [
    { hreflang: 'en', href: absoluteUrl(en) },
    { hreflang: 'es', href: absoluteUrl(es) },
    { hreflang: 'x-default', href: absoluteUrl(en) },
  ];
}
