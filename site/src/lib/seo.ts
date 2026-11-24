// Canonical address and hreflang of a page (spec stage 6 §3): canonical https://arcanadiary.com{path}; en, es and
// x-default = EN for a page whose pair in pairs.json points back at it and when both sides are indexable; a page
// without such a pair — or whose pair is a hidden service page (owner decision 35) — gets no hreflang at all (spec
// stage 2 §3: no pair, no hreflang; controller decision C: a pair only when both sides are indexable).
import { hreflangPair, langOf } from './routes';
import { hiddenPaths } from './textPages';

export const SITE_URL = 'https://arcanadiary.com';
/** Share picture of a page without its own card scan (no 1200 × 630 picture exists yet). */
export const DEFAULT_IMAGE = '/og/og-en.jpg'; // stage 7.2: 1200×630 share image (tools/site/og/make_og.mjs)
export const defaultImage = (lang: 'en' | 'es'): string => `/og/og-${lang}.jpg`;

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

let defaultHidden: ReadonlySet<string> | undefined;

/** hreflang set of an indexable page: call only for indexable page paths. [] when the page has no mutual pair or
 * either side is hidden (`hidden`: the hidden service pages, by default those of src/data/facts.json). */
export function alternates(path: string, hidden: ReadonlySet<string> = (defaultHidden ??= hiddenPaths())): Alternate[] {
  const lang = langOf(path);
  const pair = hreflangPair(path);
  if (pair === null || hidden.has(path) || hidden.has(pair)) return [];
  const en = lang === 'en' ? path : pair;
  const es = lang === 'es' ? path : pair;
  return [
    { hreflang: 'en', href: absoluteUrl(en) },
    { hreflang: 'es', href: absoluteUrl(es) },
    { hreflang: 'x-default', href: absoluteUrl(en) },
  ];
}
