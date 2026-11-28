// The Card of the Day as a habit (stage 8.1, spec 2026-11-27 §2): the streak line, the evening mark's hour, the
// calendar's address and its requests — GET /api/daily/calendar and PUT /api/daily/{day}. A mark and a note go only
// to these two requests: never to an event, never to a model.
import { callJson, withQuery, type ApiResult, type FetchFn } from './api';
import { pagePath } from './routes';
import type { Felt, Lang } from './types';

export const CALENDAR_TAB = 'daily';
export const DAILY_NOTE_MAX = 280;
export const EVENING_HOUR = 17;
export const STREAK_SHOWN_FROM = 2; // "Day 1 in a row" says nothing: the line starts on the second day

/** "Your month in cards": the Card of the Day tab of the diary. */
export function calendarHref(lang: Lang): string {
  return `${pagePath('diary', lang)}?tab=${CALENDAR_TAB}`;
}

/** The evening question shows from 17:00 local time (spec §2.3). */
export function eveningOpen(now: Date): boolean {
  return now.getHours() >= EVENING_HOUR;
}

export interface CalendarDay {
  day: string;
  card: { card_id: string; name: string; reversed: boolean };
  text: string;
  source: 'cache' | 'fallback';
  felt?: Felt | null; // an account only
  note?: string | null;
}

export interface Calendar {
  guest: boolean;
  today: string;
  month: string | null;
  months: string[]; // the free months, oldest first
  locked: boolean;
  streak: number;
  best_streak: number;
  top_card: { card_id: string; name: string; count: number } | null;
  days: CalendarDay[];
}

export interface MarkPatch {
  felt?: Felt | null;
  note?: string | null;
}

export interface MarkSaved {
  day: string;
  felt: Felt | null;
  note: string | null;
  noted_at: string | null;
}

export interface JournalApi {
  calendar(lang: Lang, month: string | undefined, tz: string | undefined): Promise<ApiResult<Calendar>>;
  mark(day: string, patch: MarkPatch): Promise<ApiResult<MarkSaved>>;
}

export function createJournalApi(fetchFn: FetchFn): JournalApi {
  return {
    calendar: (lang, month, tz) => callJson(fetchFn, withQuery('/api/daily/calendar', { lang, month, tz })),
    mark: (day, patch) => callJson(fetchFn, `/api/daily/${encodeURIComponent(day)}`, {
      method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(patch),
    }),
  };
}
