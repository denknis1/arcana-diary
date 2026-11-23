// Card lists of the hubs (spec stage 6 §5): the 22 Major Arcana, the four suits, the yes/no verdicts — from the
// deck, never from the text. No suit themes or elements (owner decision 10).
import meaningsEn from '../data/meanings.en.json';
import meaningsEs from '../data/meanings.es.json';
import { DECK, cardName, type DeckCard } from './deck';
import type { LdItem } from './jsonld';
import { cardPath, type Suit } from './routes';
import type { Lang, Vote } from './types';

export interface ListedCard {
  card: DeckCard;
  name: string;
  href: string;
}

export const SUITS: readonly Suit[] = ['wands', 'cups', 'swords', 'pentacles'];

const KEYWORDS: Readonly<Record<Lang, ReadonlyMap<string, string>>> = {
  en: new Map(meaningsEn.map((m) => [m.card_id, m.keywords[0]])),
  es: new Map(meaningsEs.map((m) => [m.card_id, m.keywords[0]])),
};

const listed = (card: DeckCard, lang: Lang): ListedCard => ({ card, name: cardName(card, lang), href: cardPath(card, lang) });

export function majorCards(lang: Lang): ListedCard[] {
  return DECK.filter((c) => c.arcana === 'major').map((c) => listed(c, lang));
}

export function suitCards(suit: Suit, lang: Lang): ListedCard[] {
  return DECK.filter((c) => c.suit === suit).map((c) => listed(c, lang));
}

export function verdictCards(verdict: Vote, lang: Lang): ListedCard[] {
  return DECK.filter((c) => c.yes_no === verdict).map((c) => listed(c, lang));
}

export function firstKeyword(card: DeckCard, lang: Lang): string {
  return KEYWORDS[lang].get(card.card_id) ?? '';
}

export function ldItems(cards: readonly ListedCard[]): LdItem[] {
  return cards.map((c) => ({ name: c.name, path: c.href }));
}
