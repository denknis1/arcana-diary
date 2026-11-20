import { describe, expect, it } from 'vitest';
import {
  CLOSED, DEAL_MS, FLIP_INTERVAL_MS, allRevealed, answerVisible, followupNow, nightReducer, readingShown, statusKey,
  crisisPayloadOf, isCrisisAction, transitionEvents, type NightAction, type NightState,
} from './nightRoom';
import type { CrisisPayload, ReadingCreated, ReadingView } from './types';

const THREE: ReadingCreated = {
  id: 'r1', lang: 'en', kind: 'three', verdict: null, soft_line: null, remaining: 2,
  cards: [
    { card_id: 'major-16-tower', position: 'past', reversed: false, name: 'The Tower' },
    { card_id: 'major-18-moon', position: 'present', reversed: true, name: 'The Moon' },
    { card_id: 'major-19-sun', position: 'path', reversed: false, name: 'The Sun' },
  ],
};
const CRISIS = { group: 'crisis', crisis: { title: 'T' }, helplines: { country: 'US', source: 'timezone', lines: [] } } as unknown as CrisisPayload;

const run = (actions: NightAction[], start: NightState = CLOSED) => actions.reduce(nightReducer, start);
const text = (name: string, t: string): NightAction => ({ type: 'stream', event: { event: 'text', data: { name, text: t } } });
const done = (shown = 'model'): NightAction => ({ type: 'stream', event: { event: 'done', data: { answer_shown: shown } } });
const flips = (n: number): NightAction[] => Array.from({ length: n }, () => ({ type: 'flip' }) as NightAction);
const created = (reducedMotion = false): NightAction => ({ type: 'created', reading: THREE, reducedMotion });
const counts = (left: number, attempts: number): NightAction => ({ type: 'counts', counts: { followups_left: left, followup_attempts_left: attempts } });

describe('opening and dealing', () => {
  it('opens, deals face down and turns the cards one by one', () => {
    let s = run([{ type: 'open' }]);
    expect(s.phase).toBe('opening');
    expect(statusKey(s)).toBe('shuffling');
    s = nightReducer(s, created());
    expect(s).toMatchObject({ phase: 'reading', revealed: 0, remaining: 2, stream: 'waiting' });
    expect(statusKey(s)).toBe('dealtThree');
    s = run(flips(2), s);
    expect(allRevealed(s)).toBe(false);
    s = run(flips(5), s);
    expect(s.revealed).toBe(3);
    expect(allRevealed(s)).toBe(true);
  });

  it('turns the cards at once with reduced motion', () => {
    const s = run([{ type: 'open' }, created(true)]);
    expect(allRevealed(s)).toBe(true);
  });

  it('keeps each card turn under a second', () => {
    expect(FLIP_INTERVAL_MS).toBeLessThanOrEqual(1000);
    expect(DEAL_MS).toBe(600);
  });

  it('ignores a late answer after the room was closed', () => {
    expect(run([{ type: 'open' }, { type: 'close' }, created()])).toEqual(CLOSED);
    expect(run([{ type: 'failed', error: 'busy' }])).toEqual(CLOSED);
  });
});

describe('the answer', () => {
  it('waits for the cards before showing streamed text', () => {
    let s = run([{ type: 'open' }, created(), text('headline', 'A change')]);
    expect(answerVisible(s)).toBe(false);
    s = run([...flips(3)], s);
    expect(answerVisible(s)).toBe(true);
    expect(statusKey(s)).toBe('writing');
    s = nightReducer(s, done());
    expect(readingShown(s)).toBe(true);
    expect(statusKey(s)).toBe('readingReady');
  });

  it('takes the soft line from meta', () => {
    const s = run([{ type: 'open' }, created(), { type: 'stream', event: { event: 'meta', data: { soft_line: 'Cards don’t predict this.' } } }]);
    expect(s.softLine).toBe('Cards don’t predict this.');
    expect(s.stream).toBe('streaming');
  });

  it('shows the crisis answer and nothing of the reading', () => {
    const s = run([{ type: 'open' }, created(true), text('headline', 'x'), { type: 'stream', event: { event: 'crisis', data: CRISIS } }]);
    expect(s.phase).toBe('crisis');
    expect(s.crisis).toEqual(CRISIS);
    expect(s.reading).toBeNull();
    expect(s.answer.started).toBe(false);
  });

  it('shows a crisis answer of the question check without a reading', () => {
    const s = run([{ type: 'open' }, { type: 'crisis', payload: CRISIS }]);
    expect(s).toMatchObject({ phase: 'crisis', reading: null });
  });

  it('closes into the Plus card at the daily limit, other errors stay in the room', () => {
    expect(run([{ type: 'open' }, { type: 'failed', error: 'limit' }]).phase).toBe('limit');
    expect(run([{ type: 'open' }, { type: 'failed', error: 'unavailable' }])).toMatchObject({ phase: 'error', error: 'unavailable' });
  });

  it('marks a lost stream, restores it from GET and clears for a retry', () => {
    let s = run([{ type: 'open' }, created(true), text('headline', 'Half'), { type: 'streamEnded', outcome: 'lost' }]);
    expect(statusKey(s)).toBe('streamLost');
    s = nightReducer(s, { type: 'restoring' });
    expect(statusKey(s)).toBe('restoring');
    const view = {
      id: 'r1', answer: { headline: 'Whole' }, answer_shown: 'model', retries_left: 0, soft_line: null, followups_left: 2,
      followup_attempts_left: 8,
    } as unknown as ReadingView;
    s = nightReducer(s, { type: 'restored', view });
    expect(s.answer.sections).toEqual({ headline: 'Whole' });
    expect(s.counts).toEqual({ followups_left: 2, followup_attempts_left: 8 });
    expect(readingShown(s)).toBe(true);
    s = nightReducer(s, { type: 'retrying' });
    expect(s.answer.started).toBe(false);
    expect(s.stream).toBe('waiting');
  });

  it('starts the answer again on every meta, so a repeated stream never appends', () => {
    const s = run([{ type: 'open' }, created(true), text('headline', 'Half'), { type: 'stream', event: { event: 'error', data: { reason: 'db' } } },
      { type: 'stream', event: { event: 'meta', data: {} } }, text('headline', 'Whole')]);
    expect(s.answer.sections).toEqual({ headline: 'Whole' });
  });

  it('turns a stream error event into a lost stream, and done is final', () => {
    const lost = run([{ type: 'open' }, created(true), { type: 'stream', event: { event: 'error', data: { reason: 'db' } } }]);
    expect(lost.stream).toBe('lost');
    const final = run([{ type: 'open' }, created(true), text('headline', 'H'), done(), { type: 'streamEnded', outcome: 'lost' }]);
    expect(final.stream).toBe('done');
  });

  it('restores a crisis reading as the crisis answer', () => {
    const view = { ...CRISIS, id: 'r1', answer_shown: 'crisis' } as unknown as ReadingView;
    expect(run([{ type: 'open' }, created(true), { type: 'restored', view }]).phase).toBe('crisis');
  });
});

describe('follow-ups', () => {
  const shown = () => run([{ type: 'open' }, created(true), text('headline', 'H'), done()]);

  it('offers a free follow-up only under a finished model answer', () => {
    expect(followupNow(run([{ type: 'open' }, created(true), text('headline', 'H')]))).toBe('none');
    expect(followupNow(shown())).toBe('none'); // no counts yet
    expect(followupNow(nightReducer(shown(), counts(2, 8)))).toBe('free');
    const fallback = run([{ type: 'open' }, created(true), { type: 'stream', event: { event: 'fallback', data: { sections: { headline: 'Base' }, retry: true } } }, done('fallback'), counts(2, 8)]);
    expect(followupNow(fallback)).toBe('none');
  });

  it('streams a follow-up, updates the counts and offers no second one while it streams', () => {
    let s = run([counts(1, 8), { type: 'followupAsk', question: 'And work?' }], shown());
    expect(followupNow(s)).toBe('none');
    expect(statusKey(s)).toBe('writing');
    s = run([
      { type: 'followupEvent', event: { event: 'text', data: { name: 'followup', text: 'Maybe.' } } },
      { type: 'followupEvent', event: { event: 'done', data: { answer_shown: 'model', followups_left: 0, followup_attempts_left: 7 } } },
    ], s);
    expect(s.followups).toEqual([{ question: 'And work?', text: 'Maybe.', status: 'done', softLine: null, usedReading: null }]);
    expect(followupNow(s)).toBe('paid');
  });

  it('warns before a paid follow-up when the API asks (402 confirm) and counts the reading it used', () => {
    let s = run([counts(0, 6), { type: 'followupAsk', question: 'More?' },
      { type: 'followupRefused', question: 'More?', refusal: { type: 'confirm', remaining: 2 } }], shown());
    expect(s.confirm).toEqual({ question: 'More?', remaining: 2 });
    expect(s.followups).toEqual([]);
    s = run([{ type: 'followupCancel' }], s);
    expect(s.confirm).toBeNull();
    s = run([
      { type: 'followupAsk', question: 'More?' },
      { type: 'followupEvent', event: { event: 'done', data: { answer_shown: 'model', followups_left: 0, followup_attempts_left: 5, used_reading: true } } },
    ], s);
    expect(s.remaining).toBe(1);
    expect(s.followups[0].usedReading).toBe(true);
  });

  it('handles 402 confirm, 402 plus and errors without keeping the unasked question', () => {
    const asked = run([counts(0, 6), { type: 'followupAsk', question: 'More?' }], shown());
    const confirm = nightReducer(asked, { type: 'followupRefused', question: 'More?', refusal: { type: 'confirm', remaining: 1 } });
    expect(confirm).toMatchObject({ followups: [], confirm: { question: 'More?', remaining: 1 } });
    const plus = nightReducer(asked, { type: 'followupRefused', question: 'More?', refusal: { type: 'plus' } });
    expect(plus).toMatchObject({ followups: [], followupPlus: true });
    const busy = nightReducer(asked, { type: 'followupRefused', question: 'More?', refusal: { type: 'error', error: 'busy' } });
    expect(busy).toMatchObject({ followups: [], followupError: 'busy' });
  });

  it('clears everything shown on a crisis in a follow-up', () => {
    const s = run([
      counts(2, 8), { type: 'followupAsk', question: 'q' },
      { type: 'followupEvent', event: { event: 'text', data: { name: 'followup', text: 'words' } } },
      { type: 'followupEvent', event: { event: 'crisis', data: CRISIS } },
    ], shown());
    expect(s).toMatchObject({ phase: 'crisis', followups: [], reading: null });
    const refused = run([counts(2, 8), { type: 'followupAsk', question: 'q' },
      { type: 'followupRefused', question: 'q', refusal: { type: 'crisis', payload: CRISIS } }], shown());
    expect(refused.phase).toBe('crisis');
  });

  it('puts a saved answer into a follow-up whose stream broke, and announces it', () => {
    const s = run([counts(2, 8), { type: 'followupAsk', question: 'q' },
      { type: 'followupEvent', event: { event: 'text', data: { name: 'followup', text: 'Half' } } },
      { type: 'followupRestored', followup: { n: 1, question: 'q', answer: 'Whole answer', soft_line: null } }], shown());
    expect(s.followups[0]).toMatchObject({ text: 'Whole answer', status: 'done' });
    expect(statusKey(s)).toBe('followupReady');
  });

  it('marks a follow-up whose stream broke', () => {
    const s = run([counts(2, 8), { type: 'followupAsk', question: 'q' }, { type: 'followupLost', answeredBefore: 0 }], shown());
    expect(s.followups[0].status).toBe('failed');
    expect(s.followupError).toBe('network');
  });

  it('clears the partial text of a lost follow-up and remembers n and answeredBefore (M3, I2)', () => {
    const s = run([counts(2, 8), { type: 'followupAsk', question: 'q' },
      { type: 'followupEvent', event: { event: 'text', data: { name: 'followup', text: 'Half' } } },
      { type: 'followupLost', n: 3, answeredBefore: 2 }], shown());
    expect(s.followups[0]).toMatchObject({ text: '', status: 'failed', lost: { n: 3, answeredBefore: 2 } });
    const retrying = nightReducer(s, { type: 'followupRetrying' });
    expect(retrying.followups[0].status).toBe('streaming');
    expect(retrying.followupError).toBeNull();
    const restored = nightReducer(retrying, { type: 'followupRestored', followup: { n: 3, question: 'q', answer: 'Back', soft_line: null } });
    expect(restored.followups[0]).toMatchObject({ text: 'Back', status: 'done', lost: undefined });
  });
});

describe('transitionEvents', () => {
  it('reports night_open, cards_revealed and reading_shown once each', () => {
    const actions: NightAction[] = [{ type: 'open' }, created(), ...flips(3), text('headline', 'H'), done(), { type: 'streamEnded', outcome: 'done' }];
    const seen: string[] = [];
    let s = CLOSED;
    for (const a of actions) {
      const next = nightReducer(s, a);
      seen.push(...transitionEvents(s, next));
      s = next;
    }
    expect(seen).toEqual(['night_open', 'cards_revealed', 'reading_shown']);
  });
});

describe('guards', () => {
  const view = { id: 'other', status: 'done', answer: { headline: 'X' }, answer_shown: 'model', followups_left: 2,
    followup_attempts_left: 8, cards: [], kind: 'three', verdict: null, soft_line: null, retries_left: 0 } as unknown as ReadingView;

  it('ignores a restored answer of another reading', () => {
    const s = run([{ type: 'open' }, created(true), { type: 'restored', view }]);
    expect(s.stream).toBe('waiting');
    expect(s.answer.started).toBe(false);
  });

  it('applies followupLost and followupCancel only in the reading phase', () => {
    const crisis = run([{ type: 'open' }, created(true), { type: 'crisis', payload: CRISIS }]);
    expect(run([{ type: 'followupLost', answeredBefore: 0 }], crisis)).toBe(crisis);
    expect(run([{ type: 'followupCancel' }], crisis)).toBe(crisis);
    expect(run([{ type: 'followupLost', answeredBefore: 0 }])).toBe(CLOSED);
    expect(run([{ type: 'followupCancel' }])).toBe(CLOSED);
  });
});

describe('isCrisisAction (a late answer of a closed room)', () => {
  it('recognises the crisis action from create', () => {
    expect(isCrisisAction({ type: 'crisis', payload: CRISIS })).toBe(true);
    expect(crisisPayloadOf({ type: 'crisis', payload: CRISIS })).toBe(CRISIS);
  });

  it('recognises a stream crisis event', () => {
    const action: NightAction = { type: 'stream', event: { event: 'crisis', data: CRISIS } };
    expect(isCrisisAction(action)).toBe(true);
    expect(crisisPayloadOf(action)).toBe(CRISIS);
  });

  it('recognises a restored view shown as crisis', () => {
    const view = { ...CRISIS, id: 'r1', status: 'done', answer_shown: 'crisis' } as unknown as ReadingView;
    expect(isCrisisAction({ type: 'restored', view })).toBe(true);
  });

  it('does not take any other action for a crisis', () => {
    const view = { id: 'r1', status: 'done', answer_shown: 'model' } as unknown as ReadingView;
    expect(isCrisisAction({ type: 'restored', view })).toBe(false);
    expect(isCrisisAction({ type: 'stream', event: { event: 'text', data: { name: 'headline', text: 'x' } } })).toBe(false);
    expect(isCrisisAction({ type: 'created', reading: THREE, reducedMotion: false })).toBe(false);
    expect(isCrisisAction({ type: 'failed', error: 'network' })).toBe(false);
  });
});
