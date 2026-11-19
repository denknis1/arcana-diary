import { describe, expect, it } from 'vitest';
import { fallbackDailyCard } from './deck';
import { baseUrl, dailyNext, formatDay, localIsoDay, shownFromBase } from './daily';

const DAILY = { day: '2026-11-20', card: { card_id: 'major-19-sun', name: 'El Sol', reversed: true }, text: 'Hoy…', source: 'cache' as const };

describe('dailyNext', () => {
  it('shows the API card with its text', () => {
    const next = dailyNext({ ok: true, status: 200, data: DAILY }, 'es');
    expect(next.type).toBe('shown');
    if (next.type === 'shown') {
      expect(next.shown).toMatchObject({ name: 'El Sol', reversed: true, text: 'Hoy…', day: '2026-11-20', fromBase: false });
      expect(next.shown.card.image).toBe('the-sun');
    }
  });

  it('falls back to the card base on 503 and reports other errors', () => {
    expect(dailyNext({ ok: false, status: 503, error: 'unavailable', body: { reason: 'db' } }, 'en')).toEqual({ type: 'base' });
    expect(dailyNext({ ok: false, status: 429, error: 'busy', body: { reason: 'rate' } }, 'en')).toEqual({ type: 'error', error: 'busy' });
    expect(dailyNext({ ok: true, status: 200, data: { ...DAILY, card: { ...DAILY.card, card_id: 'nope' } } }, 'en').type).toBe('error');
  });
});

describe('the card from the base', () => {
  it('is the day’s card, upright, with its meaning', () => {
    const card = fallbackDailyCard('2026-11-20');
    const shown = shownFromBase('2026-11-20', 'en', [{ card_id: card.card_id, upright: 'Meaning.' }]);
    expect(shown).toMatchObject({ card, name: card.name_en, reversed: false, text: 'Meaning.', fromBase: true });
    expect(shownFromBase('2026-11-20', 'en', [])).toBeNull();
    expect(baseUrl('es')).toBe('/data/daily-es.json');
  });
});

describe('days', () => {
  it('takes the local date in the person’s time zone', () => {
    const late = new Date('2026-11-21T03:30:00Z');
    expect(localIsoDay(late, 'America/Mexico_City')).toBe('2026-11-20');
    expect(localIsoDay(late, 'Europe/Madrid')).toBe('2026-11-21');
  });

  it('writes the day in the page language', () => {
    expect(formatDay('2026-11-13', 'en')).toMatch(/Friday,? 13 November/);
    expect(formatDay('2026-11-13', 'es')).toMatch(/viernes, 13 de noviembre/);
  });
});
