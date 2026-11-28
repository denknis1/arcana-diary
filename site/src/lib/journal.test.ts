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
