import { describe, expect, it } from 'vitest';
import { dailyReminderIcs, icsText, icsTime, tomorrowAtNine } from './ics';

// the device's own clock: 22 November 2026, 23:40 local time
const NOW = new Date(2026, 10, 22, 23, 40, 5);
const ORIGIN = 'https://arcana.test';

describe('the Card of the Day reminder', () => {
  it('is tomorrow at 9:00 local time, also late at night and at the end of a month', () => {
    expect(icsTime(tomorrowAtNine(NOW), false)).toBe('20261123T090000');
    expect(icsTime(tomorrowAtNine(new Date(2026, 11, 31, 8, 0)), false)).toBe('20270101T090000');
  });

  it('is one 15-minute event with the title and link of the page language', () => {
    const text = dailyReminderIcs({ now: NOW, lang: 'es', origin: ORIGIN });
    const lines = text.split('\r\n');
    expect(text.endsWith('\r\n')).toBe(true);
    expect(lines.filter((l) => l === 'BEGIN:VEVENT')).toHaveLength(1);
    expect(lines).toContain('DTSTART:20261123T090000');
    expect(lines).toContain('DURATION:PT15M');
    expect(lines).toContain('SUMMARY:Carta del día — Arcana Diary');
    expect(lines).toContain('URL:https://arcana.test/es/carta-del-dia');
    expect(lines).toContain('UID:daily-20261123@arcanadiary.com');
    expect(lines.some((l) => l.startsWith('METHOD:'))).toBe(false); // a file to add, not an invitation (review M11)
    expect(lines.find((l) => l.startsWith('DTSTAMP:'))).toMatch(/^DTSTAMP:\d{8}T\d{6}Z$/);
    for (const line of lines) expect(new TextEncoder().encode(line).length).toBeLessThanOrEqual(75);
  });

  it('rings at the start: a display alarm at 9:00 (owner decision 11)', () => {
    const lines = dailyReminderIcs({ now: NOW, lang: 'en', origin: ORIGIN }).split('\r\n');
    const alarm = lines.slice(lines.indexOf('BEGIN:VALARM'), lines.indexOf('END:VALARM') + 1);
    expect(alarm).toEqual(['BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:Card of the Day — Arcana Diary', 'TRIGGER:PT0M',
      'END:VALARM']);
    expect(lines.indexOf('BEGIN:VALARM')).toBeGreaterThan(lines.indexOf('BEGIN:VEVENT'));
    expect(lines.indexOf('END:VALARM')).toBeLessThan(lines.indexOf('END:VEVENT'));
  });

  it('pressed twice the same day it is the same event; the next day another (review M11)', () => {
    const uid = (now: Date) => dailyReminderIcs({ now, lang: 'en', origin: ORIGIN }).split('\r\n').find((l) => l.startsWith('UID:'));
    expect(uid(new Date(2026, 10, 22, 8, 0))).toBe(uid(NOW));
    expect(uid(new Date(2026, 10, 23, 8, 0))).toBe('UID:daily-20261124@arcanadiary.com');
  });

  it('in English links /daily', () => {
    const text = dailyReminderIcs({ now: NOW, lang: 'en', origin: ORIGIN });
    expect(text).toContain('SUMMARY:Card of the Day — Arcana Diary\r\n');
    expect(text).toContain('URL:https://arcana.test/daily\r\n');
  });

  it('folds long lines at 75 octets, continuing with a space, without splitting a character', () => {
    const lines = dailyReminderIcs({ now: NOW, lang: 'en', origin: `https://arcana.test/${'ñ'.repeat(60)}` }).split('\r\n');
    for (const line of lines) expect(new TextEncoder().encode(line).length).toBeLessThanOrEqual(75);
    const unfolded = lines.join('\n').replace(/\n /g, '');
    expect(unfolded).toContain(`URL:https://arcana.test/${'ñ'.repeat(60)}/daily`);
  });

  it('escapes calendar text (RFC 5545 §3.3.11; review M10)', () => {
    expect(icsText('a, b; c\\d\ne')).toBe('a\\, b\\; c\\\\d\\ne');
  });
});
