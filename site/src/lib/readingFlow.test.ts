import { describe, expect, it } from 'vitest';
import { createApi } from './api';
import { CLOSED, nightReducer, type NightAction, type NightState } from './nightRoom';
import {
  DEFAULT_COUNTS, RESTORE_TRIES, askFollowup, loadCounts, restoreReading, retryFollowup, startReading, streamReading, type FlowDeps,
} from './readingFlow';
import { brokenSseResponse, fakeFetch, jsonResponse, sseResponse, sseText } from './testing/fakes';

const CREATED = {
  id: 'r1', lang: 'en', kind: 'one', verdict: null, soft_line: null, remaining: 2,
  cards: [{ card_id: 'major-18-moon', position: 'card', reversed: false, name: 'The Moon' }],
};
const STREAM = sseText([
  ['meta', { reading_id: 'r1', soft_line: null }], ['section', { name: 'headline' }],
  ['text', { name: 'headline', text: 'Slow down.' }], ['done', { answer_shown: 'model' }],
]);
const VIEW = { id: 'r1', status: 'done', answer: { headline: 'Slow down.' }, answer_shown: 'model', retries_left: 0,
  soft_line: null, followups_left: 2, followup_attempts_left: 8, cards: CREATED.cards, kind: 'one', verdict: null,
  followups: [] as Array<{ n: number; question: string; answer: string | null; soft_line: string | null }> };

function harness(...responses: Array<Response | Error>) {
  const { fetch, calls } = fakeFetch(...responses);
  const actions: NightAction[] = [];
  const tokens: string[] = [];
  let state: NightState = nightReducer(CLOSED, { type: 'open' });
  const deps: FlowDeps = {
    api: createApi(fetch),
    dispatch: (a) => { actions.push(a); state = nightReducer(state, a); },
    turnstileToken: async (sitekey) => { tokens.push(sitekey); return sitekey === 'none' ? null : 'tok-1'; },
    sleep: async () => {},
    reducedMotion: true,
  };
  return { deps, calls, actions, tokens, state: () => state };
}

describe('startReading', () => {
  it('creates, streams and loads the follow-up counts', async () => {
    const h = harness(jsonResponse(201, CREATED), sseResponse(STREAM), jsonResponse(200, VIEW));
    await startReading(h.deps, { lang: 'en', kind: 'one', tz: 'UTC' });
    expect(h.calls.map((c) => c.url)).toEqual(['/api/readings', '/api/readings/r1/stream?tz=UTC', '/api/readings/r1?tz=UTC']);
    expect(h.state()).toMatchObject({ phase: 'reading', stream: 'done', counts: { followups_left: 2, followup_attempts_left: 8 } });
    expect(h.state().answer.sections.headline).toBe('Slow down.');
  });

  it('runs the invisible Turnstile check on 403 and repeats the request with the token', async () => {
    const h = harness(jsonResponse(403, { reason: 'turnstile', sitekey: '0xSITE' }), jsonResponse(201, CREATED),
      sseResponse(STREAM), jsonResponse(200, VIEW));
    await startReading(h.deps, { lang: 'en', kind: 'one' });
    expect(h.tokens).toEqual(['0xSITE']);
    expect(h.calls[1].body).toMatchObject({ turnstile_token: 'tok-1' });
    expect(h.state().stream).toBe('done');
  });

  it('shows the Turnstile error when no token comes', async () => {
    const h = harness(jsonResponse(403, { reason: 'turnstile', sitekey: 'none' }));
    await startReading(h.deps, { lang: 'en', kind: 'one' });
    expect(h.state()).toMatchObject({ phase: 'error', error: 'turnstile' });
    expect(h.calls).toHaveLength(1);
  });

  it('treats a Turnstile 403 without a sitekey as unavailable and never runs the check', async () => {
    for (const body of [{ reason: 'turnstile', sitekey: '' }, { reason: 'turnstile' }]) {
      const h = harness(jsonResponse(403, body));
      await startReading(h.deps, { lang: 'en', kind: 'one' });
      expect(h.tokens).toEqual([]);
      expect(h.state()).toMatchObject({ phase: 'error', error: 'unavailable' });
      expect(h.calls).toHaveLength(1);
    }
  });

  it('goes to the Plus card on 429 limit and shows a crisis answer without a reading', async () => {
    const limit = harness(jsonResponse(429, { reason: 'limit', remaining: 0 }));
    await startReading(limit.deps, { lang: 'en', kind: 'three' });
    expect(limit.state().phase).toBe('limit');
    const crisis = harness(jsonResponse(200, { group: 'crisis', crisis: {}, helplines: { lines: [] }, remaining: 3 }));
    await startReading(crisis.deps, { lang: 'en', kind: 'three', question: '…' });
    expect(crisis.state()).toMatchObject({ phase: 'crisis', reading: null });
    expect(crisis.calls).toHaveLength(1);
  });
});

describe('a broken stream', () => {
  it('restores the answer the API kept writing', async () => {
    const h = harness(jsonResponse(201, CREATED), brokenSseResponse(sseText([['meta', {}]])),
      jsonResponse(200, { ...VIEW, status: 'streaming' }), jsonResponse(200, VIEW));
    await startReading(h.deps, { lang: 'en', kind: 'one' });
    expect(h.state()).toMatchObject({ stream: 'done', counts: { followups_left: 2 } });
    expect(h.actions.map((a) => a.type)).toContain('restored');
  });

  it('streams again when nobody is writing, without looping', async () => {
    const h = harness(jsonResponse(200, { ...VIEW, status: 'pending', answer: null }), brokenSseResponse(''));
    h.deps.dispatch({ type: 'created', reading: CREATED as never, reducedMotion: true });
    await restoreReading(h.deps, 'r1', undefined);
    expect(h.calls.map((c) => c.url)).toEqual(['/api/readings/r1', '/api/readings/r1/stream']);
    expect(h.state().stream).toBe('lost');
  });

  it('gives up after a bounded number of tries', async () => {
    const h = harness(...Array.from({ length: RESTORE_TRIES }, () => new TypeError('offline')));
    h.deps.dispatch({ type: 'created', reading: CREATED as never, reducedMotion: true });
    await restoreReading(h.deps, 'r1', undefined);
    expect(h.calls).toHaveLength(RESTORE_TRIES);
    expect(h.state().stream).toBe('lost');
  });

  it('keeps the saved answer when the API refuses a retry', async () => {
    const h = harness(jsonResponse(409, { reason: 'retries' }), jsonResponse(200, { ...VIEW, answer_shown: 'fallback', answer: { headline: 'Base' } }));
    h.deps.dispatch({ type: 'created', reading: CREATED as never, reducedMotion: true });
    await streamReading(h.deps, 'r1', undefined, 'retry');
    expect(h.state()).toMatchObject({ phase: 'reading', stream: 'done' });
    expect(h.state().answer.sections).toEqual({ headline: 'Base' });
  });

  it('retries a fallback answer with POST /retry', async () => {
    const h = harness(sseResponse(STREAM), jsonResponse(200, VIEW));
    h.deps.dispatch({ type: 'created', reading: CREATED as never, reducedMotion: true });
    await streamReading(h.deps, 'r1', 'UTC', 'retry');
    expect(h.calls[0]).toMatchObject({ url: '/api/readings/r1/retry?tz=UTC', method: 'POST' });
    expect(h.state().stream).toBe('done');
  });
});

describe('opening stream answers with an HTTP error', () => {
  it('restores the saved answer when the stream answers 503', async () => {
    const h = harness(jsonResponse(201, CREATED), jsonResponse(503, { reason: 'db' }), jsonResponse(200, VIEW));
    await startReading(h.deps, { lang: 'en', kind: 'one' });
    expect(h.state()).toMatchObject({ phase: 'reading', stream: 'done' });
    expect(h.state().answer.sections.headline).toBe('Slow down.');
  });

  it('keeps other error kinds as errors', async () => {
    const h = harness(jsonResponse(201, CREATED), jsonResponse(404, {}));
    await startReading(h.deps, { lang: 'en', kind: 'one' });
    expect(h.state()).toMatchObject({ phase: 'error', error: 'gone' });
    expect(h.calls).toHaveLength(2);
  });
});

describe('askFollowup', () => {
  const ready = (...responses: Array<Response | Error>) => {
    const h = harness(...responses);
    h.deps.dispatch({ type: 'created', reading: CREATED as never, reducedMotion: true });
    h.deps.dispatch({ type: 'stream', event: { event: 'text', data: { name: 'headline', text: 'H' } } });
    h.deps.dispatch({ type: 'stream', event: { event: 'done', data: { answer_shown: 'model' } } });
    return h;
  };

  it('sends the question with the same tz and streams the answer', async () => {
    const h = ready(sseResponse(sseText([['text', { name: 'followup', text: 'Yes, gently.' }],
      ['done', { answer_shown: 'model', followups_left: 1, followup_attempts_left: 7 }]])));
    await askFollowup(h.deps, 'r1', 'And work?', 'Europe/Madrid', false, 0);
    expect(h.calls[0].body).toEqual({ question: 'And work?', tz: 'Europe/Madrid', use_reading: false });
    expect(h.state().followups[0]).toMatchObject({ text: 'Yes, gently.', status: 'done' });
    expect(h.state().counts).toEqual({ followups_left: 1, followup_attempts_left: 7 });
  });

  it('asks for confirmation on 402 confirm and sends use_reading only after it', async () => {
    const h = ready(jsonResponse(402, { reason: 'confirm', remaining: 2 }),
      sseResponse(sseText([['done', { answer_shown: 'model', followups_left: 0, followup_attempts_left: 5, used_reading: true }]])));
    await askFollowup(h.deps, 'r1', 'More?', undefined, false, 0);
    expect(h.state().confirm).toEqual({ question: 'More?', remaining: 2 });
    await askFollowup(h.deps, 'r1', 'More?', undefined, true, 0);
    expect(h.calls[1].body).toEqual({ question: 'More?', use_reading: true });
    expect(h.state().remaining).toBe(1);
  });

  it('reads back the answer of a follow-up whose stream broke', async () => {
    const saved = { n: 1, question: 'q', answer: 'Saved answer.', soft_line: null };
    const h = ready(brokenSseResponse(sseText([['text', { name: 'followup', text: 'Sav' }]])),
      jsonResponse(200, { ...VIEW, status: 'done' }),
      jsonResponse(200, { ...VIEW, followups: [saved], followups_left: 1, followup_attempts_left: 7 }));
    await askFollowup(h.deps, 'r1', ' q ', undefined, false, 0);
    expect(h.state().followups[0]).toMatchObject({ text: 'Saved answer.', status: 'done' });
    expect(h.state().counts).toEqual({ followups_left: 1, followup_attempts_left: 7 });
    expect(h.state().followupError).toBeNull();
  });

  it('restores via GET when the follow-up request itself fails before any answer', async () => {
    const saved = { n: 1, question: 'q', answer: 'Saved anyway.', soft_line: null };
    const h = ready(new TypeError('offline'), jsonResponse(200, { ...VIEW, followups: [saved], followups_left: 1, followup_attempts_left: 7 }));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    expect(h.calls.map((c) => c.url)).toEqual(['/api/readings/r1/followups', '/api/readings/r1']);
    expect(h.state().followups[0]).toMatchObject({ text: 'Saved anyway.', status: 'done' });
    expect(h.state().counts).toEqual({ followups_left: 1, followup_attempts_left: 7 });
  });

  it('does not take an older saved answer for the same question as the new one', async () => {
    const first = { n: 1, question: 'q', answer: 'Old answer.', soft_line: null };
    const second = { n: 2, question: 'q', answer: 'New answer.', soft_line: null };
    const h = ready(brokenSseResponse(''), jsonResponse(200, { ...VIEW, followups: [first] }),
      jsonResponse(200, { ...VIEW, followups: [first, second], followups_left: 0, followup_attempts_left: 6 }));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 1);
    expect(h.calls).toHaveLength(3);
    expect(h.state().followups.at(-1)).toMatchObject({ text: 'New answer.', status: 'done' });
  });

  it('on a lost follow-up dispatches followupLost, then reloads the counts', async () => {
    const h = ready(brokenSseResponse(''), ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, VIEW)),
      jsonResponse(200, { ...VIEW, followups_left: 0, followup_attempts_left: 6 }));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    const types = h.actions.map((a) => a.type);
    expect(types.slice(-2)).toEqual(['followupLost', 'counts']);
  });

  it('gives up on a lost follow-up after a bounded number of tries and resyncs the counts', async () => {
    const h = ready(brokenSseResponse(''), ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, VIEW)),
      jsonResponse(200, { ...VIEW, followups_left: 1, followup_attempts_left: 7 }));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    expect(h.state().followups[0].status).toBe('failed');
    expect(h.state().followupError).toBe('network');
    expect(h.state().counts).toEqual({ followups_left: 1, followup_attempts_left: 7 });
  });

  it('Try again on a lost follow-up reads it back with the same n and sends no new POST (I2)', async () => {
    const f = (n: number) => ({ n, question: 'q', answer: `A${n}`, soft_line: null });
    const h = ready(brokenSseResponse(sseText([['meta', { followup: 2 }], ['text', { name: 'followup', text: 'Hal' }]])),
      ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, { ...VIEW, followups: [f(1)] })),
      jsonResponse(200, { ...VIEW, followups: [f(1)] }), // counts after the loss
      jsonResponse(200, { ...VIEW, followups: [f(1), f(2)], followups_left: 0, followup_attempts_left: 5 }));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 1);
    const lost = h.state().followups[0];
    expect(lost).toMatchObject({ status: 'failed', text: '', lost: { n: 2, answeredBefore: 1 } });
    const posts = () => h.calls.filter((c) => c.url.endsWith('/followups')).length;
    expect(posts()).toBe(1);
    await retryFollowup(h.deps, 'r1', undefined, lost.lost!);
    expect(posts()).toBe(1);
    expect(h.state().followups[0]).toMatchObject({ text: 'A2', status: 'done' });
    expect(h.state().followupError).toBeNull();
    expect(h.state().counts).toEqual({ followups_left: 0, followup_attempts_left: 5 });
  });

  it('with the number from meta restores exactly that follow-up, never an earlier one', async () => {
    const f = (n: number) => ({ n, question: 'q', answer: `A${n}`, soft_line: null });
    const stale = () => jsonResponse(200, { ...VIEW, followups: [f(1), f(2)] });
    const h = ready(brokenSseResponse(sseText([['meta', { followup: 3 }]])), stale(), stale(), stale(),
      jsonResponse(200, { ...VIEW, followups: [f(1), f(2), f(3)], followups_left: 0, followup_attempts_left: 5 }));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 1);
    expect(h.calls).toHaveLength(5);
    expect(h.state().followups.at(-1)).toMatchObject({ text: 'A3', status: 'done' });
  });

  it('with the number from meta and that follow-up never listed, ends lost and reloads the counts', async () => {
    const f = (n: number) => ({ n, question: 'q', answer: `A${n}`, soft_line: null });
    const h = ready(brokenSseResponse(sseText([['meta', { followup: 3 }]])),
      ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, { ...VIEW, followups: [f(1), f(2)] })),
      jsonResponse(200, { ...VIEW, followups: [f(1), f(2)], followups_left: 0, followup_attempts_left: 4 }));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 1);
    expect(h.actions.map((a) => a.type).slice(-2)).toEqual(['followupLost', 'counts']);
    expect(h.state().followups.at(-1)?.status).toBe('failed');
    expect(h.state().counts).toEqual({ followups_left: 0, followup_attempts_left: 4 });
  });

  it('does not poll for a restore after a crisis in a broken follow-up stream', async () => {
    const h = ready(brokenSseResponse(sseText([['meta', { followup: 1 }], ['crisis', { group: 'crisis' }]])));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    expect(h.calls).toHaveLength(1);
    expect(h.state()).toMatchObject({ phase: 'crisis', followupError: null });
  });

  it('offers follow-ups with the defaults when the counts cannot be read', async () => {
    const h = ready(new TypeError('offline'), new TypeError('offline'));
    await loadCounts(h.deps, 'r1', undefined);
    expect(h.state().counts).toEqual(DEFAULT_COUNTS);
  });
});
