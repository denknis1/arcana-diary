import { describe, expect, it } from 'vitest';
import { createApi } from './api';
import { CLOSED, nightReducer, type NightAction, type NightState } from './nightRoom';
import {
  DEFAULT_COUNTS, REPEAT_WAIT_MS, RESTORE_TRIES, askFollowup, loadCounts, restoreReading, retryFollowup, startReading, streamReading, type FlowDeps,
} from './readingFlow';
import { brokenSseResponse, fakeFetch, jsonResponse, sseResponse, sseText, type Call } from './testing/fakes';

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
  let ids = 0;
  const sleeps: number[] = [];
  const deps: FlowDeps = {
    api: createApi(fetch),
    dispatch: (a) => { actions.push(a); state = nightReducer(state, a); },
    turnstileToken: async (sitekey) => { tokens.push(sitekey); return sitekey === 'none' ? null : 'tok-1'; },
    sleep: async (ms) => { sleeps.push(ms); },
    reducedMotion: true,
    newId: () => `id-${++ids}`,
  };
  return { deps, calls, actions, tokens, sleeps, state: () => state };
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
    expect(h.calls[1].body).toMatchObject({ turnstile_token: 'tok-1', request_id: 'id-1' }); // the same press of Draw
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
    expect(h.calls[0].body).toEqual({ question: 'And work?', tz: 'Europe/Madrid', use_reading: false, request_id: 'id-1' });
    expect(h.state().followups[0]).toMatchObject({ text: 'Yes, gently.', status: 'done' });
    expect(h.state().counts).toEqual({ followups_left: 1, followup_attempts_left: 7 });
  });

  it('asks for confirmation on 402 confirm and sends use_reading only after it', async () => {
    const h = ready(jsonResponse(402, { reason: 'confirm', remaining: 2 }),
      sseResponse(sseText([['done', { answer_shown: 'model', followups_left: 0, followup_attempts_left: 5, used_reading: true }]])));
    await askFollowup(h.deps, 'r1', 'More?', undefined, false, 0);
    expect(h.state().confirm).toEqual({ question: 'More?', remaining: 2 });
    await askFollowup(h.deps, 'r1', 'More?', undefined, true, 0);
    expect(h.calls[1].body).toEqual({ question: 'More?', use_reading: true, request_id: 'id-2' }); // a new press, a new number
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

  it('restores via GET when the follow-up request and its one repeat both get no answer', async () => {
    const saved = { n: 1, question: 'q', answer: 'Saved anyway.', soft_line: null };
    const h = ready(new TypeError('offline'), new TypeError('offline'),
      jsonResponse(200, { ...VIEW, followups: [saved], followups_left: 1, followup_attempts_left: 7 }));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    expect(h.calls.map((c) => c.url)).toEqual(['/api/readings/r1/followups', '/api/readings/r1/followups', '/api/readings/r1']);
    expect(h.calls[1].body).toEqual(h.calls[0].body); // the same request_id
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
    const h = ready(brokenSseResponse(''), ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, VIEW)), IN_PROGRESS(),
      jsonResponse(200, { ...VIEW, followups_left: 0, followup_attempts_left: 6 }));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    const types = h.actions.map((a) => a.type);
    expect(types.slice(-2)).toEqual(['followupLost', 'counts']);
  });

  it('gives up on a lost follow-up after a bounded number of tries and resyncs the counts', async () => {
    const h = ready(brokenSseResponse(''), ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, VIEW)), IN_PROGRESS(),
      jsonResponse(200, { ...VIEW, followups_left: 1, followup_attempts_left: 7 }));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    expect(h.state().followups[0].status).toBe('failed');
    expect(h.state().followupError).toBe('network');
    expect(h.state().counts).toEqual({ followups_left: 1, followup_attempts_left: 7 });
  });

  /** A follow-up whose ask, A1 re-POST and GET read-back all failed: the room has it lost, with its body. */
  const lostHarness = async (...after: Array<Response | Error>) => {
    const f = (n: number) => ({ n, question: 'q', answer: `A${n}`, soft_line: null });
    const h = ready(brokenSseResponse(sseText([['meta', { followup: 2 }], ['text', { name: 'followup', text: 'Hal' }]])),
      ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, { ...VIEW, followups: [f(1)] })), IN_PROGRESS(), // A1 re-POST
      jsonResponse(200, { ...VIEW, followups: [f(1)] }), // counts after the loss
      ...after);
    await askFollowup(h.deps, 'r1', 'q', undefined, true, 1);
    return { h, f, lost: h.state().followups[0] };
  };
  const posts = (h: { calls: Call[] }) => h.calls.filter((c) => c.url.endsWith('/followups'));

  it('Try again on a lost follow-up re-POSTs the same body (same request_id, use_reading) and shows the saved answer (I2)', async () => {
    const { h, lost } = await lostHarness(
      sseResponse(sseText([['meta', { followup: 2, replay: true }], ['text', { name: 'followup', text: 'A2' }],
        ['done', { answer_shown: 'model', followups_left: 0, followup_attempts_left: 5, used_reading: true }]])));
    expect(lost).toMatchObject({ status: 'failed', text: '', lost: { n: 2, answeredBefore: 1 } });
    expect(posts(h)).toHaveLength(2); // the first ask and its one A1 re-POST
    await retryFollowup(h.deps, 'r1', undefined, lost.lost!);
    const sent = posts(h);
    expect(sent).toHaveLength(3);
    expect(sent[2].body).toEqual(sent[0].body); // never a new number, never another use_reading
    expect(sent[2].body).toMatchObject({ request_id: 'id-1', use_reading: true });
    expect(h.state().followups[0]).toMatchObject({ text: 'A2', status: 'done' });
    expect(h.state().followupError).toBeNull();
  });

  it('Try again reaches a crisis tombstone: the crisis event replaces the lost follow-up with the help screen (I2)', async () => {
    const { h, lost } = await lostHarness(sseResponse(sseText([['meta', { followup: 2, replay: true }], ['crisis', { group: 'crisis', crisis: {}, helplines: { lines: [] } }]])));
    await retryFollowup(h.deps, 'r1', undefined, lost.lost!);
    expect(posts(h)[2].body).toEqual(posts(h)[0].body);
    expect(h.state().phase).toBe('crisis');
  });

  it('Try again shows a crisis JSON answer of the re-POST too (I2)', async () => {
    const { h, lost } = await lostHarness(jsonResponse(200, { group: 'crisis', crisis: {}, helplines: { lines: [] }, remaining: 3 }));
    await retryFollowup(h.deps, 'r1', undefined, lost.lost!);
    expect(h.state().phase).toBe('crisis');
  });

  it('Try again that gets in_progress falls back to the GET read-back for the same n', async () => {
    const f = (n: number) => ({ n, question: 'q', answer: `A${n}`, soft_line: null });
    const { h, lost } = await lostHarness(sseResponse(sseText([['meta', { followup: 2, replay: true }], ['error', { reason: 'in_progress' }]])),
      jsonResponse(200, { ...VIEW, followups: [f(1), f(2)], followups_left: 0, followup_attempts_left: 5 }));
    await retryFollowup(h.deps, 'r1', undefined, lost.lost!);
    expect(posts(h)).toHaveLength(3); // one re-POST, never a second new ask
    expect(h.state().followups[0]).toMatchObject({ text: 'A2', status: 'done' });
    expect(h.state().counts).toEqual({ followups_left: 0, followup_attempts_left: 5 });
  });

  it('Try again that gets no answer stays lost, keeps the body and sends no other POST (I2)', async () => {
    const { h, lost } = await lostHarness(new TypeError('offline'),
      ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, { ...VIEW, followups: [] })), jsonResponse(200, VIEW));
    await retryFollowup(h.deps, 'r1', undefined, lost.lost!);
    const sent = posts(h);
    expect(sent).toHaveLength(3);
    expect(sent.every((c) => JSON.stringify(c.body) === JSON.stringify(sent[0].body))).toBe(true);
    expect(h.state().followups[0]).toMatchObject({ status: 'failed', lost: { n: 2, answeredBefore: 1 } });
    expect(h.state().followups[0].lost?.body).toMatchObject({ request_id: 'id-1', use_reading: true });
  });

  it('Try again that gets a 503 keeps the follow-up lost with its body and button: one POST, then the GET (Minor 1)', async () => {
    const { h, lost } = await lostHarness(jsonResponse(503, {}),
      ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, { ...VIEW, followups: [] })), jsonResponse(200, VIEW));
    await retryFollowup(h.deps, 'r1', undefined, lost.lost!);
    expect(posts(h)).toHaveLength(3); // the ask, its A1 re-POST, this one re-POST
    expect(h.calls.at(-1)?.method).toBe('GET');
    expect(h.actions.some((a, i) => i > 0 && a.type === 'followupRefused')).toBe(false);
    expect(h.state().followups).toHaveLength(1);
    expect(h.state().followups[0]).toMatchObject({ status: 'failed', lost: { n: 2, answeredBefore: 1 } });
    expect(h.state().followups[0].lost?.body).toMatchObject({ request_id: 'id-1', use_reading: true });
  });

  it('Try again answered 402 plus leaves followupPlus, 429 attempts leaves the refusal state', async () => {
    const plus = await lostHarness(jsonResponse(402, { reason: 'plus', remaining: 0 }));
    await retryFollowup(plus.h.deps, 'r1', undefined, plus.lost.lost!);
    expect(plus.h.state().followupPlus).toBe(true);
    expect(plus.h.state().followups).toHaveLength(0);
    const rate = await lostHarness(jsonResponse(429, { reason: 'attempts' }));
    await retryFollowup(rate.h.deps, 'r1', undefined, rate.lost.lost!);
    expect(rate.h.state().followupError).toBe('attempts');
    expect(rate.h.state().followups).toHaveLength(0);
  });

  it('Try again on a follow-up without a number falls back to the GET read-back only', async () => {
    const f = { n: 1, question: 'q', answer: 'Saved.', soft_line: null };
    const h = ready(jsonResponse(200, { ...VIEW, followups: [f], followups_left: 1, followup_attempts_left: 7 }));
    h.deps.dispatch({ type: 'followupAsk', question: 'q' });
    h.deps.dispatch({ type: 'followupLost', answeredBefore: 0 }); // no body, no request_id
    await retryFollowup(h.deps, 'r1', undefined, { answeredBefore: 0 });
    expect(posts(h)).toHaveLength(0);
    expect(h.state().followups[0]).toMatchObject({ text: 'Saved.', status: 'done' });
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
      ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, { ...VIEW, followups: [f(1), f(2)] })), IN_PROGRESS(),
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

const IN_PROGRESS = () => sseResponse(sseText([['meta', { followup: 1, replay: true }], ['error', { reason: 'in_progress' }]]));

describe('one request, one reading (spec 4.5 §5)', () => {
  it('sends a new number with every press of Draw', async () => {
    const h = harness(jsonResponse(201, CREATED), sseResponse(STREAM), jsonResponse(200, VIEW),
      jsonResponse(201, CREATED), sseResponse(STREAM), jsonResponse(200, VIEW));
    await startReading(h.deps, { lang: 'en', kind: 'yes_no', count: 3 });
    await startReading(h.deps, { lang: 'en', kind: 'yes_no', count: 3 });
    const posts = h.calls.filter((c) => c.url === '/api/readings');
    expect(posts.map((c) => c.body)).toEqual([
      { lang: 'en', kind: 'yes_no', count: 3, request_id: 'id-1' }, { lang: 'en', kind: 'yes_no', count: 3, request_id: 'id-2' },
    ]);
  });

  it('repeats a draw that got no answer once, with the same number, and shows the reading it gives', async () => {
    const h = harness(new TypeError('offline'), jsonResponse(201, CREATED), sseResponse(STREAM), jsonResponse(200, VIEW));
    await startReading(h.deps, { lang: 'en', kind: 'one' });
    expect(h.calls.map((c) => c.url).slice(0, 2)).toEqual(['/api/readings', '/api/readings']);
    expect(h.calls[1].body).toEqual(h.calls[0].body);
    expect(h.sleeps[0]).toBe(REPEAT_WAIT_MS); // a second between the two tries
    expect(h.state()).toMatchObject({ phase: 'reading', stream: 'done' });
  });

  it('repeats only once, then shows the usual offline error', async () => {
    const h = harness(new TypeError('offline'), new TypeError('offline'));
    await startReading(h.deps, { lang: 'en', kind: 'one' });
    expect(h.calls).toHaveLength(2);
    expect(h.state()).toMatchObject({ phase: 'error', error: 'network' });
  });

  it('never repeats a draw that got an answer, even an error', async () => {
    const h = harness(jsonResponse(503, { reason: 'unavailable' }));
    await startReading(h.deps, { lang: 'en', kind: 'one' });
    expect(h.calls).toHaveLength(1);
    expect(h.state()).toMatchObject({ phase: 'error', error: 'unavailable' });
  });

  const ready = (...responses: Array<Response | Error>) => {
    const h = harness(...responses);
    h.deps.dispatch({ type: 'created', reading: CREATED as never, reducedMotion: true });
    h.deps.dispatch({ type: 'stream', event: { event: 'text', data: { name: 'headline', text: 'H' } } });
    h.deps.dispatch({ type: 'stream', event: { event: 'done', data: { answer_shown: 'model' } } });
    return h;
  };

  it('repeats a follow-up that got no answer once with the same number and shows the stream it gives', async () => {
    const replay = sseText([['meta', { followup: 1, replay: true, soft_line: null }], ['section', { name: 'followup' }],
      ['text', { name: 'followup', text: 'Saved.' }], ['done', { answer_shown: 'model', followups_left: 1, followup_attempts_left: 7 }]]);
    const h = ready(new TypeError('offline'), sseResponse(replay));
    await askFollowup(h.deps, 'r1', 'q', 'UTC', false, 0);
    expect(h.calls).toHaveLength(2);
    expect(h.calls[0].body).toEqual({ question: 'q', tz: 'UTC', use_reading: false, request_id: 'id-1' });
    expect(h.calls[1].body).toEqual(h.calls[0].body);
    expect(h.sleeps).toEqual([REPEAT_WAIT_MS]);
    expect(h.state().followups).toHaveLength(1);
    expect(h.state().followups[0]).toMatchObject({ text: 'Saved.', status: 'done' });
  });

  it('reads back a repeated follow-up that the API is still writing', async () => {
    const saved = { n: 1, question: 'q', answer: 'Written meanwhile.', soft_line: null };
    const h = ready(new TypeError('offline'), sseResponse(sseText([['meta', { followup: 1, replay: true }], ['error', { reason: 'in_progress' }]])),
      jsonResponse(200, { ...VIEW, followups: [] }),
      jsonResponse(200, { ...VIEW, followups: [saved], followups_left: 1, followup_attempts_left: 7 }));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    expect(h.calls.map((c) => c.method)).toEqual(['POST', 'POST', 'GET', 'GET']);
    expect(h.state().followups[0]).toMatchObject({ text: 'Written meanwhile.', status: 'done' });
  });

  it('sends a new number with every follow-up', async () => {
    const done = (left: number) => sseResponse(sseText([['done', { answer_shown: 'model', followups_left: left, followup_attempts_left: 7 }]]));
    const h = ready(done(1), done(0));
    await askFollowup(h.deps, 'r1', 'one', undefined, false, 0);
    await askFollowup(h.deps, 'r1', 'two', undefined, false, 1);
    expect(h.calls.map((c) => (c.body as { request_id: string }).request_id)).toEqual(['id-1', 'id-2']);
  });

  it('A1: lost after the GET restore, posts once more with the same number and body and shows the replayed answer', async () => {
    const replay = sseText([['meta', { followup: 1, replay: true, soft_line: null }], ['section', { name: 'followup' }],
      ['text', { name: 'followup', text: 'Replayed.' }], ['done', { answer_shown: 'model', followups_left: 1, followup_attempts_left: 7 }]]);
    const h = ready(brokenSseResponse(sseText([['meta', { followup: 1 }], ['text', { name: 'followup', text: 'Hal' }]])),
      ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, { ...VIEW, followups: [] })), sseResponse(replay));
    await askFollowup(h.deps, 'r1', 'q', 'UTC', false, 0);
    const posts = h.calls.filter((c) => c.method === 'POST');
    expect(posts).toHaveLength(2);
    expect(posts[1].body).toEqual(posts[0].body);
    expect((posts[1].body as { request_id: string }).request_id).toBe('id-1');
    expect(h.calls).toHaveLength(RESTORE_TRIES + 2); // 1 POST + the GETs + 1 re-POST, no more
    expect(h.state().followups).toHaveLength(1);
    expect(h.state().followups[0]).toMatchObject({ text: 'Replayed.', status: 'done' }); // no leftover partial text
    expect(h.state().counts).toEqual({ followups_left: 1, followup_attempts_left: 7 });
  });

  it('A1: a replayed crisis (the tombstone) takes the room to the crisis phase, with no third request', async () => {
    const h = ready(brokenSseResponse(''),
      ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, { ...VIEW, followups: [] })),
      sseResponse(sseText([['meta', { followup: 1, replay: true }], ['crisis', { group: 'crisis', crisis: {}, helplines: { lines: [] } }]])));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    expect(h.state().phase).toBe('crisis');
    expect(h.calls.filter((c) => c.method === 'POST')).toHaveLength(2);
    expect(h.calls).toHaveLength(RESTORE_TRIES + 2);
  });

  it('A1: in_progress on the re-POST leaves the follow-up lost and restorable, with only one re-POST', async () => {
    const h = ready(brokenSseResponse(''),
      ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, { ...VIEW, followups: [] })), IN_PROGRESS(),
      jsonResponse(200, { ...VIEW, followups: [], followups_left: 1, followup_attempts_left: 7 }));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    expect(h.calls.filter((c) => c.method === 'POST')).toHaveLength(2);
    expect(h.state().followups[0]).toMatchObject({ status: 'failed', text: '', lost: { answeredBefore: 0 } });
    expect(h.state().followupError).toBe('network');
  });

  const CRISIS_JSON = { group: 'crisis', crisis: {}, helplines: { lines: [] } };
  const lostThen = (repostResponse: Response, first = brokenSseResponse(sseText([['meta', { followup: 1 }], ['text', { name: 'followup', text: 'Hal' }]]))) =>
    ready(first, ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, { ...VIEW, followups: [] })), repostResponse,
      jsonResponse(200, { ...VIEW, followups: [], followups_left: 1, followup_attempts_left: 7 }));

  it('I1: the re-POST answered with a crisis JSON takes the room to the crisis phase', async () => {
    const h = lostThen(jsonResponse(200, CRISIS_JSON));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    expect(h.state().phase).toBe('crisis');
    expect(h.calls.filter((c) => c.method === 'POST')).toHaveLength(2);
  });

  it('I1: the re-POST answered 402 plus or 429 leaves the matching refusal, no lost follow-up to retry', async () => {
    const plus = lostThen(jsonResponse(402, { error: 'plus_required' }));
    await askFollowup(plus.deps, 'r1', 'q', undefined, false, 0);
    expect(plus.state().followupPlus).toBe(true);
    expect(plus.state().followups).toHaveLength(0);
    const rate = lostThen(jsonResponse(429, { error: 'rate_limited' }));
    await askFollowup(rate.deps, 'r1', 'q', undefined, false, 0);
    expect(rate.state().followups).toHaveLength(0);
    expect(rate.state().followupError).not.toBeNull();
    expect(rate.state().followupError).not.toBe('network');
  });

  it('A1: the re-POST answered 503 leaves the follow-up lost with its body and button (Minor 1)', async () => {
    const h = lostThen(jsonResponse(503, {}));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    expect(h.calls.filter((c) => c.method === 'POST')).toHaveLength(2);
    expect(h.actions.some((a) => a.type === 'followupRefused')).toBe(false);
    expect(h.state().followups).toHaveLength(1);
    expect(h.state().followups[0]).toMatchObject({ status: 'failed', lost: { n: 1, answeredBefore: 0 } });
    expect(h.state().followups[0].lost?.body).toMatchObject({ request_id: 'id-1' });
    expect(h.state().followupError).toBe('network');
  });

  it('M1: the number from the re-POST meta (in_progress) is what Try again restores by', async () => {
    const h = lostThen(sseResponse(sseText([['meta', { followup: 3, replay: true }], ['error', { reason: 'in_progress' }]])),
      brokenSseResponse(sseText([['text', { name: 'followup', text: 'Hal' }]]))); // the first stream never got its meta
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    expect(h.state().followups[0].lost).toMatchObject({ n: 3, answeredBefore: 0 });
  });

  it('M2: a re-POST that ends with a fallback answer clears the lost marker', async () => {
    const h = lostThen(sseResponse(sseText([['meta', { followup: 1, replay: true }],
      ['fallback', { sections: { followup: 'Fallback.' } }], ['done', { answer_shown: 'fallback', followups_left: 1, followup_attempts_left: 7 }]])));
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    expect(h.state().followups[0]).toMatchObject({ text: 'Fallback.', status: 'failed' });
    expect(h.state().followups[0].lost).toBeUndefined();
  });

  it('M3: a re-POST does not append to text left by a stream that ended with an error event', async () => {
    const first = sseResponse(sseText([['meta', { followup: 1 }], ['text', { name: 'followup', text: 'Hal' }], ['error', { reason: 'upstream' }]]));
    const h = lostThen(sseResponse(sseText([['meta', { followup: 1, replay: true }], ['text', { name: 'followup', text: 'Whole.' }],
      ['done', { answer_shown: 'model', followups_left: 1, followup_attempts_left: 7 }]])), first);
    await askFollowup(h.deps, 'r1', 'q', undefined, false, 0);
    expect(h.state().followups[0]).toMatchObject({ text: 'Whole.', status: 'done' });
  });
});
