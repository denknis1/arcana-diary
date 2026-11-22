// "Remind me tomorrow" under the Card of the Day (spec 4.4b §7): a calendar file made in the browser — one event
// tomorrow at 9:00 local time (a floating time, so the calendar keeps 9:00 wherever the person is), 15 minutes,
// with the link to the Card of the Day and an alarm at its start (owner decision 11: on an iPhone an event without
// one passes silently). No server, no personal data. The UID names the day: two presses give one event (M11).
import { pagePath } from './routes';
import type { Lang } from './types';

export const ICS_FILENAME = 'arcana-diary-card-of-the-day.ics';
export const ICS_TYPE = 'text/calendar;charset=utf-8';
const TITLES: Record<Lang, string> = { en: 'Card of the Day — Arcana Diary', es: 'Carta del día — Arcana Diary' };

const two = (n: number) => String(n).padStart(2, '0');

/** Tomorrow, 9:00 in the device's time zone (the calendar date moves first, so month, year and DST ends are right). */
export function tomorrowAtNine(now: Date): Date {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 9, 0, 0);
}

/** 20261123T090000 (local, floating) or 20261122T103000Z (UTC). */
export function icsTime(date: Date, utc: boolean): string {
  if (utc) {
    return `${date.getUTCFullYear()}${two(date.getUTCMonth() + 1)}${two(date.getUTCDate())}T${two(date.getUTCHours())}${two(date.getUTCMinutes())}${two(date.getUTCSeconds())}Z`;
  }
  return `${date.getFullYear()}${two(date.getMonth() + 1)}${two(date.getDate())}T${two(date.getHours())}${two(date.getMinutes())}${two(date.getSeconds())}`;
}

/** RFC 5545 text: backslash, semicolon, comma and new lines escaped. */
export function icsText(text: string): string {
  return text.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
}

const encoder = new TextEncoder();

/** RFC 5545 §3.1: lines of at most 75 octets; the rest continues on the next line after one space. Never splits a character. */
export function foldLine(line: string): string {
  const parts: string[] = [];
  let current = '';
  let size = 0;
  for (const ch of line) {
    const bytes = encoder.encode(ch).length;
    const limit = parts.length === 0 ? 75 : 74; // continuation lines start with a space
    if (size + bytes > limit) {
      parts.push(current);
      current = '';
      size = 0;
    }
    current += ch;
    size += bytes;
  }
  parts.push(current);
  return parts.join('\r\n ');
}

export function dailyReminderIcs(input: { now: Date; lang: Lang; origin: string }): string {
  const start = tomorrowAtNine(input.now);
  const link = `${input.origin}${pagePath('daily', input.lang)}`;
  const title = icsText(TITLES[input.lang]);
  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Arcana Diary//Card of the Day//EN',
    'CALSCALE:GREGORIAN',
    'BEGIN:VEVENT',
    `UID:daily-${icsTime(start, false).slice(0, 8)}@arcanadiary.com`,
    `DTSTAMP:${icsTime(input.now, true)}`,
    `DTSTART:${icsTime(start, false)}`,
    'DURATION:PT15M',
    `SUMMARY:${title}`,
    `DESCRIPTION:${icsText(link)}`,
    `URL:${link}`,
    'BEGIN:VALARM',
    'ACTION:DISPLAY',
    `DESCRIPTION:${title}`,
    'TRIGGER:PT0M',
    'END:VALARM',
    'END:VEVENT',
    'END:VCALENDAR',
  ];
  return `${lines.map(foldLine).join('\r\n')}\r\n`;
}
