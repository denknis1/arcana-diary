// The diary's rules for the screen (spec 4.4b §5): which entry the address opens, how an entry is named, when
// "Came true / Partly / No" opens (00:00 local time of the 7th day after the reading's day — owner decision 13), the
// note's length, the outcome event's `after_days`.
import type { DictKey } from '../i18n';
import type { DiaryItem } from './accountApi';
import { pagePath } from './routes';
import type { Kind, Lang } from './types';

export const OUTCOME_AFTER_DAYS = 7; // owner decision 6
export const DAY_MS = 24 * 60 * 60 * 1000;
export const NOTE_MAX = 1000; // spec 4.3 §6
export const DIARY_PAGE = 10; // the free diary shows 10 (spec 4.4b §5): one request holds them all, no "Show more"

const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** `?r=<id>` of the diary page: the entry to open, or null for the list. */
export function entryParam(search: string): string | null {
  const id = new URLSearchParams(search).get('r');
  return id && ID.test(id) ? id.toLowerCase() : null;
}

export function entryHref(lang: Lang, id: string): string {
  return `${pagePath('diary', lang)}?r=${encodeURIComponent(id)}`;
}

/** The moment "did it come true?" opens (owner decision 13): 00:00 local time of the day «the reading's local date + 7
 * days». The "Come back on {date}" line names this day, so the line and the buttons always agree (review I7). */
export function outcomeOpensOn(createdAt: string): Date {
  const made = new Date(createdAt);
  return new Date(made.getFullYear(), made.getMonth(), made.getDate() + OUTCOME_AFTER_DAYS);
}

export function outcomeOpen(createdAt: string, now: Date): boolean {
  return now.getTime() >= outcomeOpensOn(createdAt).getTime();
}

/** `after_days` of `outcome_answered` (docs/design/analytics-events.md): 7 up to 30 days after, then 30. */
export function afterDays(createdAt: string, now: Date): 7 | 30 {
  return now.getTime() - new Date(createdAt).getTime() < 30 * DAY_MS ? 7 : 30;
}

/** "20 November 2026" / "20 de noviembre de 2026", in the person's own time zone. */
export function formatDate(iso: string | Date, lang: Lang, timeZone?: string): string {
  const date = typeof iso === 'string' ? new Date(iso) : iso;
  return new Intl.DateTimeFormat(lang === 'en' ? 'en-GB' : 'es-MX', { day: 'numeric', month: 'long', year: 'numeric', timeZone }).format(date);
}

/** How a diary entry is named: by the tool it came from. */
export function kindKey(kind: Kind, topic: string | null): DictKey {
  if (topic === 'love') return 'navLove';
  if (kind === 'yes_no') return 'navYesNo';
  if (kind === 'three') return 'diaryKindThree';
  return 'fmtOneCard';
}

export function noteLeft(text: string): number {
  return NOTE_MAX - text.length;
}

/** A crisis entry is listed without any text (the API sends none); everything else may show its question. */
export function isCrisis(item: Pick<DiaryItem, 'answer_shown'>): boolean {
  return item.answer_shown === 'crisis';
}
