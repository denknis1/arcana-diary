import { describe, expect, it } from 'vitest';
import { createApi, withQuery } from './api';
import type { SseEvent } from './sse';
import { brokenSseResponse, fakeFetch, jsonResponse, slowSseResponse, sseResponse, sseText, stalledSseResponse } from './testing/fakes';

const CREATED = {
  id: 'r1', lang: 'en', kind: 'three', soft_line: null, verdict: null, remaining: 2,
  cards: [{ card_id: 'major-16-tower', position: 'past', reversed: false, name: 'The Tower' }],
};
const CRISIS = { group: 'crisis', crisis: { title: 'You don’t have to carry this alone' }, helplines: { lines: [] }, remaining: 3 };

describe('createReading', () => {
  it('posts the body as JSON and returns the reading', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(201, CREATED));
    const result = await createApi(fetch).createReading({ lang: 'en', kind: 'three', question: 'Move?', tz: 'Europe/Madrid' });
    expect(result).toEqual({ type: 'reading', reading: CREATED });
    expect(calls[0]).toMatchObject({
      url: '/api/readings', method: 'POST', body: { lang: 'en', kind: 'three', question: 'Move?', tz: 'Europe/Madrid' },
    });
  });

  it('returns the crisis answer, never a reading', async () => {
    const { fetch } = fakeFetch(jsonResponse(200, CRISIS));
    expect(await createApi(fetch).createReading({ lang: 'en', kind: 'one' })).toEqual({ type: 'crisis', payload: CRISIS });
  });

  it('classifies refusals and network failures', async () => {
    const { fetch } = fakeFetch(
      jsonResponse(429, { reason: 'limit', remaining: 0 }),
      jsonResponse(403, { reason: 'turnstile', sitekey: '0xSITE' }),
      new TypeError('offline'),
    );
    const api = createApi(fetch);
    expect(await api.createReading({ lang: 'en', kind: 'one' })).toEqual({ type: 'error', error: 'limit', body: { reason: 'limit', remaining: 0 } });
    expect(await api.createReading({ lang: 'en', kind: 'one' })).toMatchObject({ type: 'error', error: 'turnstile', body: { sitekey: '0xSITE' } });
    expect(await api.createReading({ lang: 'en', kind: 'one' })).toEqual({ type: 'error', error: 'network', body: null });
  });
});

describe('streams', () => {
  it('reads the reading stream with the same tz', async () => {
    const text = sseText([['meta', { reading_id: 'r1' }], ['done', { answer_shown: 'model' }]]);
    const { fetch, calls } = fakeFetch(sseResponse(text));
    const events: SseEvent[] = [];
    const end = await createApi(fetch).streamReading('r1', 'America/Mexico_City', (e) => events.push(e));
    expect(end).toEqual({ type: 'ended' });
    expect(events.map((e) => e.event)).toEqual(['meta', 'done']);
    expect(calls[0].url).toBe('/api/readings/r1/stream?tz=America%2FMexico_City');
    expect(calls[0].headers.accept).toBe('text/event-stream');
  });

  it('reports a broken stream after passing on what arrived', async () => {
    const { fetch } = fakeFetch(brokenSseResponse(sseText([['section', { name: 'headline' }]])));
    const events: SseEvent[] = [];
    expect(await createApi(fetch).streamReading('r1', undefined, (e) => events.push(e))).toEqual({ type: 'broken' });
    expect(events).toHaveLength(1);
  });

  it('turns a JSON refusal of a stream into an error', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(409, { reason: 'retries' }));
    expect(await createApi(fetch).retryReading('r1', 'UTC', () => {})).toEqual({ type: 'error', error: 'other', body: { reason: 'retries' } });
    expect(calls[0]).toMatchObject({ url: '/api/readings/r1/retry?tz=UTC', method: 'POST' });
  });
});

describe('follow-ups', () => {
  it('streams an answer', async () => {
    const { fetch, calls } = fakeFetch(sseResponse(sseText([['text', { name: 'followup', text: 'Yes.' }]])));
    const events: SseEvent[] = [];
    const result = await createApi(fetch).postFollowup('r1', { question: 'And work?', tz: 'UTC', use_reading: false }, (e) => events.push(e));
    expect(result).toEqual({ type: 'stream', end: { type: 'ended' } });
    expect(calls[0]).toMatchObject({ url: '/api/readings/r1/followups', method: 'POST', body: { question: 'And work?', tz: 'UTC', use_reading: false } });
    expect(events).toHaveLength(1);
  });

  it('turns 402 confirm, 402 plus and a crisis answer into refusals', async () => {
    const { fetch } = fakeFetch(
      jsonResponse(402, { reason: 'confirm', remaining: 2 }),
      jsonResponse(402, { reason: 'plus', remaining: 0 }),
      jsonResponse(200, CRISIS),
      jsonResponse(429, { reason: 'attempts' }),
    );
    const api = createApi(fetch);
    const ask = () => api.postFollowup('r1', { question: 'q', use_reading: false }, () => {});
    expect(await ask()).toEqual({ type: 'refused', refusal: { type: 'confirm', remaining: 2 } });
    expect(await ask()).toEqual({ type: 'refused', refusal: { type: 'plus' } });
    expect(await ask()).toEqual({ type: 'refused', refusal: { type: 'crisis', payload: CRISIS } });
    expect(await ask()).toEqual({ type: 'refused', refusal: { type: 'error', error: 'attempts' } });
  });

  it('reports a request that throws as no answer at all (to be repeated, then restored), not a refusal', async () => {
    const { fetch } = fakeFetch(new TypeError('offline'));
    const result = await createApi(fetch).postFollowup('r1', { question: 'q', use_reading: false, request_id: 'n-1' }, () => {});
    expect(result).toEqual({ type: 'noResponse' });
  });
});

describe('other calls', () => {
  it('gets the reading, the card of the day and joins the Plus waitlist', async () => {
    const { fetch, calls } = fakeFetch(
      jsonResponse(200, { id: 'r1', status: 'done' }),
      jsonResponse(503, { reason: 'db' }),
      jsonResponse(200, { ok: true }),
    );
    const api = createApi(fetch);
    expect(await api.getReading('r1', 'UTC')).toEqual({ ok: true, status: 200, data: { id: 'r1', status: 'done' } });
    expect(await api.getDaily('es', 'America/Bogota')).toEqual({ ok: false, status: 503, error: 'unavailable', body: { reason: 'db' } });
    expect(await api.joinWaitlist('ana@example.com', 'es')).toEqual({ ok: true, status: 200, data: { ok: true } });
    expect(calls.map((c) => c.url)).toEqual(['/api/readings/r1?tz=UTC', '/api/daily?lang=es&tz=America%2FBogota', '/api/plus/waitlist']);
    expect(calls[2].body).toEqual({ email: 'ana@example.com', lang: 'es' });
  });

  it('leaves out empty query values', () => {
    expect(withQuery('/api/daily', { lang: 'en', tz: undefined })).toBe('/api/daily?lang=en');
    expect(withQuery('/x', {})).toBe('/x');
  });
});

describe('idle watchdog', () => {
  const IDLE = 30;

  it('ends a stalled reading stream as broken, after passing on what arrived', async () => {
    const { fetch, signals } = fakeFetch(stalledSseResponse(sseText([['section', { name: 'headline' }]])));
    const events: SseEvent[] = [];
    const end = await createApi(fetch, { idleMs: IDLE }).streamReading('r1', undefined, (e) => events.push(e));
    expect(end).toEqual({ type: 'broken' });
    expect(events).toHaveLength(1);
    expect(signals[0]?.aborted).toBe(true);
  });

  it('ends a stalled retry as broken', async () => {
    const { fetch } = fakeFetch(stalledSseResponse());
    expect(await createApi(fetch, { idleMs: IDLE }).retryReading('r1', undefined, () => {})).toEqual({ type: 'broken' });
  });

  it('ends a stalled follow-up as stream/broken', async () => {
    const { fetch } = fakeFetch(stalledSseResponse());
    const result = await createApi(fetch, { idleMs: IDLE }).postFollowup('r1', { question: 'q', use_reading: false }, () => {});
    expect(result).toEqual({ type: 'stream', end: { type: 'broken' } });
  });

  it('aborts while waiting for the response headers', async () => {
    const hanging: Parameters<typeof createApi>[0] = (_url, init) =>
      new Promise((_resolve, reject) => init?.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError'))));
    const api = createApi(hanging, { idleMs: IDLE });
    expect(await api.streamReading('r1', undefined, () => {})).toEqual({ type: 'broken' });
    expect(await api.postFollowup('r1', { question: 'q', use_reading: false }, () => {})).toEqual({ type: 'noResponse' });
  });

  it('gives up on POST /api/readings that does not answer in time (a network error, spec 4.5 §5)', async () => {
    const signals: Array<AbortSignal | undefined> = [];
    const hanging: Parameters<typeof createApi>[0] = (_url, init) => {
      signals.push(init?.signal ?? undefined);
      return new Promise((_resolve, reject) => init?.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError'))));
    };
    const result = await createApi(hanging, { createTimeoutMs: IDLE }).createReading({ lang: 'en', kind: 'one', request_id: 'n-1' });
    expect(result).toEqual({ type: 'error', error: 'network', body: null });
    expect(signals[0]?.aborted).toBe(true);
  });

  it('does not abort a stream that keeps sending chunks more often than the idle time', async () => {
    const pieces = ['a', 'b', 'c', 'd', 'e', 'f'].map((n) => sseText([['text', { name: n }]]));
    const { fetch, signals } = fakeFetch(slowSseResponse(pieces, 20));
    const events: SseEvent[] = [];
    const end = await createApi(fetch, { idleMs: 200 }).streamReading('r1', undefined, (e) => events.push(e));
    expect(end).toEqual({ type: 'ended' });
    expect(events).toHaveLength(6);
    expect(signals[0]?.aborted).toBe(false);
  });

  it('clears the timer on a normal end (no late abort)', async () => {
    const { fetch, signals } = fakeFetch(sseResponse(sseText([['done', {}]])));
    expect(await createApi(fetch, { idleMs: 10 }).streamReading('r1', undefined, () => {})).toEqual({ type: 'ended' });
    await new Promise((resolve) => setTimeout(resolve, 40));
    expect(signals[0]?.aborted).toBe(false);
  });
});
