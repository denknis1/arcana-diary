// Addresses of the 4.4a pages (spec 2026-11-19 stage 4.4a §3) and their language pairs
// (site/src/data/pairs.json, from docs/research/stage2/hreflang.csv via tools/site/sync_site_data.py).
import pairsData from '../data/pairs.json';
import { DECK, cardSlug, type DeckCard } from './deck';
import type { Lang } from './types';

export type PageKey = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily' | 'not_found';

/** Where the 429 / 403 / 503 messages and the footer send people who need help now (§10.8 of spec 4.2). */
export const HELP_URL = 'https://findahelpline.com';

const PAIRS: Readonly<Record<string, string>> = pairsData;
const NOT_FOUND_PAIRS: Readonly<Record<string, string>> = { '/404': '/es/404', '/es/404': '/404' };

const PAGE_PATHS: Record<Lang, Record<PageKey, string>> = {
  en: { home: '/', one_card: '/one-card', yes_no: '/yes-no', love: '/love', daily: '/daily', not_found: '/404' },
  // Spanish has no one-card page: the one-card mode is the #una-carta section of the home page (stage 2 map)
  es: {
    home: '/es', one_card: '/es#una-carta', yes_no: '/es/si-o-no', love: '/es/amor', daily: '/es/carta-del-dia',
    not_found: '/es/404',
  },
};

/** The menu (stage 2 structure, design screens 11c/11d). "Card Meanings" and the diary arrive with stages 6 and
 * 4.4b; until then the menu has these four items. */
export const NAV_KEYS: readonly PageKey[] = ['home', 'yes_no', 'love', 'daily'];

export function pagePath(key: PageKey, lang: Lang): string {
  return PAGE_PATHS[lang][key];
}

export function cardPath(card: DeckCard, lang: Lang): string {
  return lang === 'en' ? `/cards/${cardSlug(card, 'en')}` : `/es/cartas/${cardSlug(card, 'es')}`;
}

export function langOf(path: string): Lang {
  return path === '/es' || path.startsWith('/es/') || path.startsWith('/es#') ? 'es' : 'en';
}

/** The other language's address for the language switch; a page without a pair goes to that language's home. */
export function switchPath(path: string): string {
  const pair = PAIRS[path] ?? NOT_FOUND_PAIRS[path];
  if (pair) return pair;
  return langOf(path) === 'en' ? '/es' : '/';
}

/** Every page the build must produce, both languages: tools, 78 card pages each, 404. */
export function allPagePaths(): string[] {
  const tools = (lang: Lang) =>
    (Object.keys(PAGE_PATHS[lang]) as PageKey[]).map((key) => PAGE_PATHS[lang][key]).filter((p) => !p.includes('#'));
  return [...tools('en'), ...DECK.map((c) => cardPath(c, 'en')), ...tools('es'), ...DECK.map((c) => cardPath(c, 'es'))];
}

/** The file Astro writes for a path with build.format "file" (served by Caddy's try_files {path}.html). */
export function distFile(path: string): string {
  return path === '/' ? 'index.html' : `${path.slice(1)}.html`;
}
