import { describe, expect, it } from 'vitest';
import { EVENTS_URL, analyticsEvent, sendEvent } from './analytics';

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
