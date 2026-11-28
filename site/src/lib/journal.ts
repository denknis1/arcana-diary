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

const LOCALE: Record<Lang, string> = { en: 'en-US', es: 'es-MX' };

/** The weeks of a month "YYYY-MM", Sunday first (as in the United States and Mexico); null pads the first and last
 * week. Each day is "YYYY-MM-DD". */
export function monthGrid(month: string): Array<Array<string | null>> {
  const [year, number] = month.split('-').map(Number);
  const days = new Date(Date.UTC(year, number, 0)).getUTCDate();
  const cells: Array<string | null> = Array(new Date(Date.UTC(year, number - 1, 1)).getUTCDay()).fill(null);
  for (let day = 1; day <= days; day++) cells.push(`${month}-${String(day).padStart(2, '0')}`);
  while (cells.length % 7) cells.push(null);
  return Array.from({ length: cells.length / 7 }, (_, week) => cells.slice(week * 7, week * 7 + 7));
}

/** "November 2026" / "noviembre de 2026". */
export function monthLabel(month: string, lang: Lang): string {
  const [year, number] = month.split('-').map(Number);
  return new Intl.DateTimeFormat(LOCALE[lang], { month: 'long', year: 'numeric', timeZone: 'UTC' })
    .format(new Date(Date.UTC(year, number - 1, 1)));
}

/** Short weekday names, Sunday first: "Sun"… / "dom"…. */
export function weekdayLabels(lang: Lang): string[] {
  const format = new Intl.DateTimeFormat(LOCALE[lang], { weekday: 'short', timeZone: 'UTC' });
  return Array.from({ length: 7 }, (_, i) => format.format(new Date(Date.UTC(2026, 10, 1 + i)))); // 1.11.2026: Sunday
}

/** The days of a guest's calendar: the last `count` days up to `today`, oldest first. */
export function lastDays(today: string, count = 7): string[] {
  const end = Date.parse(`${today}T00:00:00Z`);
  return Array.from({ length: count }, (_, i) => new Date(end - (count - 1 - i) * 86_400_000).toISOString().slice(0, 10));
}
