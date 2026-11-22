import { describe, expect, it } from 'vitest';
import { EVENTS_URL, analyticsEvent, sendEvent, type EventName } from './analytics';

describe('analyticsEvent', () => {
  it('builds the whitelisted shape', () => {
    expect(analyticsEvent('draw_click', 'yes_no', 'es', { has_question: true, entry: 'tool' })).toEqual({
      name: 'draw_click', tool: 'yes_no', lang: 'es', params: { has_question: true, entry: 'tool' },
    });
    expect(analyticsEvent('tool_view', 'home', 'en')).toEqual({ name: 'tool_view', tool: 'home', lang: 'en', params: {} });
  });

  it('sends plus_view without a tool', () => {
    expect(analyticsEvent('plus_view', 'home', 'en', { place: 'limit' }).tool).toBeNull();
  });

  it('knows the events of stage 4.4b (spec §8): signup_done and outcome_answered without a tool', () => {
    expect(analyticsEvent('save_click', 'love', 'es')).toEqual({ name: 'save_click', tool: 'love', lang: 'es', params: {} });
    expect(analyticsEvent('remind_click', 'daily', 'en')).toEqual({ name: 'remind_click', tool: 'daily', lang: 'en', params: {} });
    expect(analyticsEvent('signup_done', null, 'en', { method: 'google' })).toEqual({
      name: 'signup_done', tool: null, lang: 'en', params: { method: 'google' },
    });
    expect(analyticsEvent('outcome_answered', 'home', 'es', { after_days: 7, answer: 'partly' }).tool).toBeNull();
    expect(analyticsEvent('plus_view', null, 'en', { place: 'diary' }).params).toEqual({ place: 'diary' });
  });

  it('types: an event with a tool needs one, remind_click comes only from the daily card (review Minor 1; astro check verifies)', () => {
    // @ts-expect-error draw_click names its tool
    expect(analyticsEvent('draw_click', null, 'en').tool).toBeNull();
    // @ts-expect-error save_click names its tool
    expect(analyticsEvent('save_click', null, 'es').tool).toBeNull();
    // @ts-expect-error remind_click is the daily card's only
    expect(analyticsEvent('remind_click', 'love', 'en').tool).toBe('love');
    const anyName = 'tool_view' as EventName;
    // @ts-expect-error a name that may be a tool event needs a tool
    expect(analyticsEvent(anyName, null, 'en').tool).toBeNull();
    const roomEvent = 'reading_shown' as 'night_open' | 'cards_revealed' | 'reading_shown';
    expect(analyticsEvent(roomEvent, 'home', 'en').tool).toBe('home');
    expect(analyticsEvent('outcome_answered', null, 'en').tool).toBeNull();
  });
});

describe('sendEvent', () => {
  const event = analyticsEvent('reading_shown', 'home', 'en', { ms_from_draw: 4200 });

  it('uses sendBeacon with a JSON blob', async () => {
    const sent: Array<[string, Blob]> = [];
    sendEvent(event, { sendBeacon: (url, data) => { sent.push([url, data]); return true; }, fetch: () => { throw new Error('no'); } });
    expect(sent[0][0]).toBe(EVENTS_URL);
    expect(sent[0][1].type).toBe('application/json');
    expect(JSON.parse(await sent[0][1].text())).toEqual(event);
  });

  it('falls back to fetch with keepalive and without cookies when the beacon is refused', () => {
    const calls: Array<[string, RequestInit]> = [];
    sendEvent(event, { sendBeacon: () => false, fetch: async (url, init) => { calls.push([url, init]); } });
    expect(calls[0][0]).toBe(EVENTS_URL);
    expect(calls[0][1]).toMatchObject({ method: 'POST', keepalive: true, credentials: 'same-origin' });
  });

  it('never throws', () => {
    expect(() => sendEvent(event, { sendBeacon: () => { throw new Error('x'); }, fetch: () => Promise.reject(new Error('y')) })).not.toThrow();
    expect(() => sendEvent(event, {})).not.toThrow();
  });
});

describe('ms_from_draw clamp', () => {
  it('sends an integer within 0..600000', () => {
    const ms = (x: number) => analyticsEvent('reading_shown', 'home', 'en', { ms_from_draw: x }).params.ms_from_draw;
    expect(ms(4200.6)).toBe(4201);
    expect(ms(-5)).toBe(0);
    expect(ms(9e9)).toBe(600000);
    expect(ms(NaN)).toBe(0);
    expect(ms(Infinity)).toBe(0);
  });
});
