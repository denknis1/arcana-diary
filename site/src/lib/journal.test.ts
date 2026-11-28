import { describe, expect, it } from 'vitest';
import { fakeFetch, jsonResponse } from './testing/fakes';
import { calendarHref, createJournalApi, eveningOpen } from './journal';

describe('the Card of the Day as a habit (stage 8.1)', () => {
  it('links the calendar tab of the diary in each language', () => {
    expect(calendarHref('en')).toBe('/diary?tab=daily');
    expect(calendarHref('es')).toBe('/es/diario?tab=daily');
  });

  it('opens the evening question at 17:00 local time', () => {
    expect(eveningOpen(new Date(2026, 10, 22, 16, 59))).toBe(false);
    expect(eveningOpen(new Date(2026, 10, 22, 17, 0))).toBe(true);
    expect(eveningOpen(new Date(2026, 10, 22, 23, 59))).toBe(true);
  });

  it('asks for a month and puts a mark with JSON', async () => {
    const served = fakeFetch(jsonResponse(200, { days: [] }), jsonResponse(200, { day: '2026-11-22', felt: 'yes', note: null, noted_at: 'x' }));
    const api = createJournalApi(served.fetch);
    await api.calendar('es', '2026-11', 'America/Mexico_City');
    const saved = await api.mark('2026-11-22', { felt: 'yes' });
    expect(served.calls.map((c) => `${c.method} ${c.url}`)).toEqual([
      'GET /api/daily/calendar?lang=es&month=2026-11&tz=America%2FMexico_City', 'PUT /api/daily/2026-11-22']);
    expect(served.calls[1].body).toEqual({ felt: 'yes' });
    expect(saved.ok && saved.data.felt).toBe('yes');
  });
});

describe('the calendar month (stage 8.1 §2.2)', () => {
  it('lays a month out in weeks from Sunday', async () => {
    const { monthGrid } = await import('./journal');
    const november = monthGrid('2026-11'); // 1 November 2026 is a Sunday
    expect(november[0]).toEqual(['2026-11-01', '2026-11-02', '2026-11-03', '2026-11-04', '2026-11-05', '2026-11-06', '2026-11-07']);
    expect(november).toHaveLength(5);
    expect(november[4]).toEqual(['2026-11-29', '2026-11-30', null, null, null, null, null]);
    const february = monthGrid('2027-02'); // starts on a Monday, 28 days
    expect(february[0][0]).toBeNull();
    expect(february.flat().filter(Boolean)).toHaveLength(28);
  });

  it('names the month and the weekdays in each language', async () => {
    const { monthLabel, weekdayLabels } = await import('./journal');
    expect(monthLabel('2026-11', 'en')).toBe('November 2026');
    expect(monthLabel('2026-11', 'es')).toBe('noviembre de 2026');
    expect(weekdayLabels('en')[0]).toBe('Sun');
    expect(weekdayLabels('es')[0]).toBe('dom');
  });

  it('gives a guest the last seven days', async () => {
    const { lastDays } = await import('./journal');
    expect(lastDays('2026-12-02')).toEqual(['2026-11-26', '2026-11-27', '2026-11-28', '2026-11-29', '2026-11-30',
      '2026-12-01', '2026-12-02']);
  });
});
