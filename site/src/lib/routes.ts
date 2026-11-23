// Addresses of the site's pages (spec 4.4a §3, stage 6 §3) and their language pairs
// (site/src/data/pairs.json, from docs/research/stage2/hreflang.csv via tools/site/sync_site_data.py).
import pairsData from '../data/pairs.json';
import { fill, t, type DictKey } from '../i18n';
import type { CardBlockId } from './cardPages';
import { DECK, cardById, cardName, cardSlug, type DeckCard } from './deck';
import type { DrawnCard, Lang, Tool, Vote } from './types';

/** The service pages of spec stage 6 §6 (EN and ES pairs, owner decision 8 of 14.11.2026). */
export type ServiceKey = 'about' | 'how_readings_work' | 'contact' | 'privacy' | 'terms';

export type PageKey = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily' | 'diary' | 'account' | 'not_found'
  | 'cards' | 'major_arcana' | 'yes_no_cards' | 'three_cards' | ServiceKey;

export const SERVICE_KEYS: readonly ServiceKey[] = ['about', 'how_readings_work', 'contact', 'privacy', 'terms'];

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
    about: '/about', how_readings_work: '/how-readings-work', contact: '/contact', privacy: '/privacy', terms: '/terms',
    three_cards: '/', // English has no three-card page: the home page is the three-card reading
  },
  // Spanish has no one-card page: the one-card mode is the #una-carta section of the home page (stage 2 map)
  es: {
    home: '/es', one_card: '/es#una-carta', yes_no: '/es/si-o-no', love: '/es/amor', daily: '/es/carta-del-dia',
    diary: '/es/diario', account: '/es/cuenta', not_found: '/es/404', cards: '/es/cartas',
    major_arcana: '/es/cartas/arcanos-mayores',
    yes_no_cards: '/es/si-o-no', // no Spanish card list: the yes/no tool
    three_cards: '/es/tiradas/3-cartas',
    about: '/es/sobre-nosotros', how_readings_work: '/es/como-funcionan-las-lecturas', contact: '/es/contacto',
    privacy: '/es/privacidad', terms: '/es/terminos',
  },
};

/** The menu (stage 2 structure, design screens 11c/11d, 13a): the diary since 4.4b, "Card Meanings" since stage 6. */
export const NAV_KEYS: readonly PageKey[] = ['home', 'yes_no', 'love', 'daily', 'cards', 'diary'];

export function pagePath(key: PageKey, lang: Lang): string {
  return PAGE_PATHS[lang][key];
}

export function cardPath(card: DeckCard, lang: Lang): string {
  return lang === 'en' ? `/cards/${cardSlug(card, 'en')}` : `/es/cartas/${cardSlug(card, 'es')}`;
}

export type SectionKey = CardBlockId | 'draw' | 'faq' | 'related' | 'about';

/** Section anchors of the card page; EN #reversed, ES #invertida, #amor, #si-o-no are rows EN-095, ES-092…094 of the
 * page maps. */
export const SECTION_IDS: Readonly<Record<Lang, Readonly<Record<SectionKey, string>>>> = {
  en: {
    on_the_card: 'on-the-card', waite: 'waite', upright: 'upright', reversed: 'reversed', love: 'love',
    work_money: 'work-and-money', advice: 'advice', yes_no: 'yes-or-no', in_a_reading: 'as-a-person',
    combinations: 'combinations', not_to_confuse: 'not-to-confuse', ask_yourself: 'ask-yourself',
    draw: 'draw', faq: 'faq', related: 'related', about: 'about',
  },
  es: {
    on_the_card: 'en-la-carta', waite: 'waite', upright: 'al-derecho', reversed: 'invertida', love: 'amor',
    work_money: 'trabajo-y-dinero', advice: 'consejo', yes_no: 'si-o-no', in_a_reading: 'como-persona',
    combinations: 'combinaciones', not_to_confuse: 'no-confundir', ask_yourself: 'preguntas-para-ti',
    draw: 'tu-pregunta', faq: 'preguntas', related: 'relacionadas', about: 'sobre-esta-pagina',
  },
};

/** One link under a drawn card: a launch row of docs/research/stage2/links-{en,es}.csv (owner decision 38). */
export interface DrawnLink {
  row: string;
  href: string;
  text: string;
}

interface DrawnRule {
  row: string;
  text: DictKey; // the row's anchor_pattern: {name} is {card_name}, {verdict} the card's own yes/no
  section?: SectionKey; // the row's to_id is a section of the card page (ES-093 #amor, ES-094 #si-o-no)
}

const full = (row: string): DrawnRule => ({ row, text: 'fullMeaning' });

/** The launch rows from each tool to the drawn card ("@drawn", ES-093, ES-094), in the order they are shown.
 * Spanish one-card readings are the #una-carta mode of the home page (ES-001) and the card page's own draw. */
const DRAWN_RULES: Readonly<Record<Lang, Readonly<Record<Tool, readonly DrawnRule[]>>>> = {
  en: {
    home: [full('L-EN-01')], three_cards: [full('L-EN-01')], one_card: [full('L-EN-02')],
    love: [full('L-EN-03')], yes_no: [full('L-EN-31')], daily: [{ row: 'L-EN-15', text: 'dailyCardLink' }],
  },
  es: {
    home: [full('L-ES-01')], one_card: [full('L-ES-01')], three_cards: [full('L-ES-02')],
    love: [{ row: 'L-ES-03', text: 'drawnLoveLink', section: 'love' }, full('L-ES-23')],
    yes_no: [{ row: 'L-ES-04', text: 'drawnWhyLink', section: 'yes_no' }],
    daily: [{ row: 'L-ES-15', text: 'dailyCardLink' }],
  },
};

const VOTE_KEYS: Readonly<Record<Vote, DictKey>> = { yes: 'voteYes', no: 'voteNo', unclear: 'voteUnclear' };

/** The card's own yes/no: the API's vote, else the rule of content/cards/yes-no-rules.json (reversed: not clear). */
function ownVote(card: Pick<DrawnCard, 'reversed' | 'vote'>, deckCard: DeckCard): Vote {
  return card.vote ?? (card.reversed ? 'unclear' : deckCard.yes_no);
}

/** The links under one drawn card for a tool (owner decision 38: the screen follows the stage 2 matrix); the card
 * name is the card base's, the verdict the yes/no label in lower case, mid-sentence. No links for an unknown card. */
export function drawnCardLink(card: Pick<DrawnCard, 'card_id' | 'reversed' | 'vote'>, tool: Tool, lang: Lang): DrawnLink[] {
  const deckCard = cardById(card.card_id);
  if (!deckCard) return [];
  const d = t(lang);
  const name = cardName(deckCard, lang);
  const verdict = d[VOTE_KEYS[ownVote(card, deckCard)]].toLocaleLowerCase(lang);
  return DRAWN_RULES[lang][tool].map((rule) => ({
    row: rule.row,
    href: rule.section ? `${cardPath(deckCard, lang)}#${SECTION_IDS[lang][rule.section]}` : cardPath(deckCard, lang),
    text: fill(d[rule.text], { name, verdict }),
  }));
}

export type Suit = 'wands' | 'cups' | 'swords' | 'pentacles';

/** The suit blocks of the hub (/cards#wands, /es/cartas#bastos): links L-EN-10, L-ES-10 of the stage 2 matrix. */
export const SUIT_IDS: Readonly<Record<Lang, Readonly<Record<Suit, string>>>> = {
  en: { wands: 'wands', cups: 'cups', swords: 'swords', pentacles: 'pentacles' },
  es: { wands: 'bastos', cups: 'copas', swords: 'espadas', pentacles: 'oros' },
};

export function suitPath(suit: Suit, lang: Lang): string {
  return `${pagePath('cards', lang)}#${SUIT_IDS[lang][suit]}`;
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
