// Card of the Day (spec 4.4a §5): GET /api/daily → tap the back → the card and its text for today. When the API
// answers 503 (no database), the site shows a card from the card base instead: the same card for everyone that
// local day, upright, with its short meaning (fetched from /data/daily-<lang>.json only at that moment).
import type { ApiResult } from './api';
import { cardById, cardName, fallbackDailyCard, type DeckCard } from './deck';
import type { ErrorKind } from './errors';
import type { DailyCard, Lang } from './types';

export interface DailyShown {
  card: DeckCard;
  name: string;
  reversed: boolean;
  text: string;
  day: string;
  fromBase: boolean; // true: the site's own card from the base (the API was unavailable)
}

export interface BaseMeaning {
  card_id: string;
  upright: string;
}

export type DailyNext = { type: 'shown'; shown: DailyShown } | { type: 'base' } | { type: 'error'; error: ErrorKind };

/** YYYY-MM-DD of `date` in the person's time zone. */
export function localIsoDay(date: Date, timeZone?: string): string {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)!.value;
  return `${get('year')}-${get('month')}-${get('day')}`;
}

/** "Friday, 20 November" / "viernes, 20 de noviembre". */
export function formatDay(isoDay: string, lang: Lang): string {
  const date = new Date(`${isoDay}T12:00:00Z`);
  return new Intl.DateTimeFormat(lang === 'en' ? 'en-GB' : 'es-MX', {
    weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC',
  }).format(date);
}

export function dailyNext(result: ApiResult<DailyCard>, lang: Lang): DailyNext {
  if (result.ok) {
    const card = cardById(result.data.card.card_id);
    if (!card) return { type: 'error', error: 'other' };
    return { type: 'shown', shown: {
      card, name: result.data.card.name || cardName(card, lang), reversed: result.data.card.reversed,
      text: result.data.text, day: result.data.day, fromBase: false,
    } };
  }
  return result.error === 'unavailable' ? { type: 'base' } : { type: 'error', error: result.error };
}

export function shownFromBase(isoDay: string, lang: Lang, meanings: readonly BaseMeaning[]): DailyShown | null {
  const card = fallbackDailyCard(isoDay);
  const meaning = meanings.find((m) => m.card_id === card.card_id);
  if (!meaning) return null;
  return { card, name: cardName(card, lang), reversed: false, text: meaning.upright, day: isoDay, fromBase: true };
}

export function baseUrl(lang: Lang): string {
  return `/data/daily-${lang}.json`;
}
