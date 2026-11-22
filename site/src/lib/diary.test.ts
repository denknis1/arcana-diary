import { describe, expect, it } from 'vitest';
import { DAY_MS, afterDays, entryHref, entryParam, formatDate, isCrisis, kindKey, noteLeft, outcomeOpen, outcomeOpensOn } from './diary';

const MADE = new Date(2026, 10, 1, 22, 0).toISOString(); // 1 November 2026, 22:00 on this device's clock
const local = (month: number, day: number, hour = 0, minute = 0) => new Date(2026, month, day, hour, minute);
const at = (days: number) => new Date(new Date(MADE).getTime() + days * DAY_MS);

describe('diary rules', () => {
  it('opens an entry only for a real reading id', () => {
    expect(entryParam('?r=2B3C4D5E-0000-4000-8000-000000000001')).toBe('2b3c4d5e-0000-4000-8000-000000000001');
    expect(entryParam('?r=../account')).toBeNull();
    expect(entryParam('')).toBeNull();
    expect(entryHref('es', 'abc')).toBe('/es/diario?r=abc');
  });

  it('opens "did it come true?" at 00:00 local time of the 7th day after the reading\'s day (owner decision 13)', () => {
    expect(outcomeOpensOn(MADE).getTime()).toBe(local(10, 8).getTime());
    expect(outcomeOpen(MADE, local(10, 7, 23, 59))).toBe(false);
    expect(outcomeOpen(MADE, local(10, 8, 0, 0))).toBe(true);
    expect(outcomeOpen(MADE, local(10, 8, 9, 0))).toBe(true); // less than 7 × 24 h after 22:00, yet the named day
  });

  it('names in the "come back" line the very day the buttons open, also across a month end', () => {
    const late = new Date(2026, 10, 30, 23, 59).toISOString();
    expect(formatDate(outcomeOpensOn(late), 'en')).toBe('7 December 2026');
    expect(outcomeOpen(late, local(11, 6, 23, 59))).toBe(false);
    expect(outcomeOpen(late, local(11, 7))).toBe(true);
  });

  it('counts after_days 7 up to 30 days, then 30', () => {
    expect(afterDays(MADE, at(7))).toBe(7);
    expect(afterDays(MADE, at(29.9))).toBe(7);
    expect(afterDays(MADE, at(30))).toBe(30);
  });

  it('formats a date in each language', () => {
    expect(formatDate('2026-11-01T12:00:00+00:00', 'en', 'UTC')).toBe('1 November 2026');
    expect(formatDate('2026-11-01T12:00:00+00:00', 'es', 'UTC')).toBe('1 de noviembre de 2026');
  });

  it('names an entry by its tool', () => {
    expect(kindKey('three', 'love')).toBe('navLove');
    expect(kindKey('yes_no', null)).toBe('navYesNo');
    expect(kindKey('three', 'work')).toBe('diaryKindThree');
    expect(kindKey('one', null)).toBe('fmtOneCard');
    expect(kindKey('card_page', null)).toBe('fmtOneCard');
  });

  it('counts the note and knows a crisis entry', () => {
    expect(noteLeft('x'.repeat(990))).toBe(10);
    expect(isCrisis({ answer_shown: 'crisis' })).toBe(true);
    expect(isCrisis({ answer_shown: 'model' })).toBe(false);
  });
});
