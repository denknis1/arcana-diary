// Canonical address and hreflang of a page (spec stage 6 §3): canonical https://arcanadiary.com{path}; en, es and
// x-default = EN for a page whose pair in pairs.json points back at it; a page without such a pair gets no hreflang
// at all (spec stage 2 §3: no pair, no hreflang).
import { hreflangPair, langOf } from './routes';

export const SITE_URL = 'https://arcanadiary.com';
/** Share picture of a page without its own card scan (no 1200 × 630 picture exists yet). */
export const DEFAULT_IMAGE = '/cards/the-moon.webp';

export interface Alternate {
  hreflang: 'en' | 'es' | 'x-default';
  href: string;
}

/** The canonical address of a path; throws on a non-canonical one (no leading "/", trailing "/" other than the home,
 * ".html", "#"). */
export function absoluteUrl(path: string): string {
  if (!path.startsWith('/') || (path.length > 1 && path.endsWith('/')) || path.endsWith('.html') || path.includes('#')) {
    throw new Error(`Non-canonical path: ${path}`);
  }
  return `${SITE_URL}${path}`;
}

/** hreflang set of an indexable page: call only for indexable page paths. [] when the page has no mutual pair. */
export function alternates(path: string): Alternate[] {
  const lang = langOf(path);
  const pair = hreflangPair(path);
  if (pair === null) return [];
  const en = lang === 'en' ? path : pair;
  const es = lang === 'es' ? path : pair;
  return [
    { hreflang: 'en', href: absoluteUrl(en) },
    { hreflang: 'es', href: absoluteUrl(es) },
    { hreflang: 'x-default', href: absoluteUrl(en) },
  ];
}
