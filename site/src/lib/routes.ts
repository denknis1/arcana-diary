// Addresses of the site's pages (spec 4.4a §3, stage 6 §3) and their language pairs
// (site/src/data/pairs.json, from docs/research/stage2/hreflang.csv via tools/site/sync_site_data.py).
import pairsData from '../data/pairs.json';
import { DECK, cardSlug, type DeckCard } from './deck';
import type { Lang } from './types';

export type PageKey = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily' | 'diary' | 'account' | 'not_found'
  | 'cards' | 'major_arcana' | 'yes_no_cards' | 'three_cards';

/** Where the 429 / 403 / 503 messages and the footer send people who need help now (§10.8 of spec 4.2). */
export const HELP_URL = 'https://findahelpline.com';

const PAIRS: Readonly<Record<string, string>> = pairsData;
const NOT_FOUND_PAIRS: Readonly<Record<string, string>> = { '/404': '/es/404', '/es/404': '/404' };
/** Spec 4.4b §5, §6: the diary and the account are noindex, outside hreflang.csv; the switch still pairs them. */
export const PRIVATE_PAIRS: Readonly<Record<string, string>> = {
  '/diary': '/es/diario', '/es/diario': '/diary', '/account': '/es/cuenta', '/es/cuenta': '/account',
};

const PAGE_PATHS: Record<Lang, Record<PageKey, string>> = {
  en: {
    home: '/', one_card: '/one-card', yes_no: '/yes-no', love: '/love', daily: '/daily', diary: '/diary',
    account: '/account', not_found: '/404', cards: '/cards', major_arcana: '/cards/major-arcana',
    yes_no_cards: '/yes-no/cards',
    three_cards: '/', // English has no three-card page: the home page is the three-card reading
  },
  // Spanish has no one-card page: the one-card mode is the #una-carta section of the home page (stage 2 map)
  es: {
    home: '/es', one_card: '/es#una-carta', yes_no: '/es/si-o-no', love: '/es/amor', daily: '/es/carta-del-dia',
    diary: '/es/diario', account: '/es/cuenta', not_found: '/es/404', cards: '/es/cartas',
    major_arcana: '/es/cartas/arcanos-mayores',
    yes_no_cards: '/es/si-o-no', // no Spanish card list: the yes/no tool
    three_cards: '/es/tiradas/3-cartas',
  },
};

/** The menu (stage 2 structure, design screens 11c/11d, 13a): the diary since 4.4b; "Card Meanings" arrives with
 * stage 6. */
export const NAV_KEYS: readonly PageKey[] = ['home', 'yes_no', 'love', 'daily', 'diary'];

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
  const pair = PAIRS[path] ?? NOT_FOUND_PAIRS[path] ?? PRIVATE_PAIRS[path];
  if (pair) return pair;
  return langOf(path) === 'en' ? '/es' : '/';
}

/** The pair for hreflang (spec stage 6 §3): only a pair that points back — /one-card → /es is a switch, not a pair. */
export function hreflangPair(path: string): string | null {
  const pair = PAIRS[path];
  return pair !== undefined && PAIRS[pair] === path ? pair : null;
}

/** Every page the build must produce, both languages: tools, hubs, the diary and the account, 78 card pages each,
 * 404. A key that points at another page of its language (three_cards in English) is listed once. */
export function allPagePaths(): string[] {
  const tools = (lang: Lang) => [...new Set((Object.keys(PAGE_PATHS[lang]) as PageKey[])
    .map((key) => PAGE_PATHS[lang][key]).filter((p) => !p.includes('#')))];
  return [...tools('en'), ...DECK.map((c) => cardPath(c, 'en')), ...tools('es'), ...DECK.map((c) => cardPath(c, 'es'))];
}

/** The file Astro writes for a path with build.format "file" (served by Caddy's try_files {path}.html). */
export function distFile(path: string): string {
  return path === '/' ? 'index.html' : `${path.slice(1)}.html`;
}
