// The 78 cards for the screens: names, slugs and pictures (site/src/data/deck.json, made by
// tools/site/sync_site_data.py from content/cards). Pictures: site/public/cards/<image>.webp (700 × 1200),
// <image>@350.webp, <image>@160.webp; the back is back.svg.
import deckData from '../data/deck.json';
import type { Lang, Vote } from './types';

export interface DeckCard {
  card_id: string;
  numeral: string;
  arcana: 'major' | 'minor';
  suit: string | null;
  yes_no: Vote; // base yes/no verdict of the card upright (content/cards/deck.json)
  image: string;
  slug_en: string;
  slug_es: string;
  name_en: string;
  name_es: string;
}

export const DECK: readonly DeckCard[] = deckData as DeckCard[];
export const CARD_BACK = '/cards/back.svg';
export type CardWidth = 160 | 350 | 700;

const BY_ID = new Map(DECK.map((card) => [card.card_id, card]));

export function cardById(cardId: string): DeckCard | undefined {
  return BY_ID.get(cardId);
}

export function cardName(card: DeckCard, lang: Lang): string {
  return lang === 'en' ? card.name_en : card.name_es;
}

export function cardSlug(card: DeckCard, lang: Lang): string {
  return lang === 'en' ? card.slug_en : card.slug_es;
}

export function cardImage(card: DeckCard, width: CardWidth): string {
  return width === 700 ? `/cards/${card.image}.webp` : `/cards/${card.image}@${width}.webp`;
}

export function cardSrcset(card: DeckCard): string {
  return `${cardImage(card, 160)} 160w, ${cardImage(card, 350)} 350w, ${cardImage(card, 700)} 700w`;
}

/** Previous and next card in deck order, wrapping at both ends. */
export function neighbors(card: DeckCard): { prev: DeckCard; next: DeckCard } {
  const i = DECK.indexOf(card);
  return { prev: DECK[(i + DECK.length - 1) % DECK.length], next: DECK[(i + 1) % DECK.length] };
}

/** When GET /api/daily answers 503 the site picks the day's card itself: the same card for everyone on that
 * local day (YYYY-MM-DD), upright, with its meaning from the card base. */
export function fallbackDailyCard(isoDay: string): DeckCard {
  let hash = 0;
  for (const ch of isoDay) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return DECK[hash % DECK.length];
}
