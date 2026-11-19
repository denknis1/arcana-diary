// The night room as a state machine (spec 4.4a §4): opening → cards dealt → cards turn (≤ 1 s each) → the
// reader's answer streams → the answer by sections → follow-ups. Pure: the island dispatches actions and draws
// the state; timers and requests live in the island and in readingFlow.ts.
import { EMPTY_ANSWER, answerFromView, applyAnswerEvent, type Answer } from './answer';
import type { DictKey } from '../i18n';
import type { ErrorKind } from './errors';
import { applyFollowupEvent, followupOffer, newFollowup, type Followup, type FollowupRefusal, type Offer } from './followups';
import type { SseEvent } from './sse';
import type { CrisisPayload, FollowupCounts, ReadingCreated, ReadingView, SavedFollowup } from './types';

/** closed — not shown; limit — closed, the panel shows the Plus card (screen 11a) instead. */
export type Phase = 'closed' | 'opening' | 'reading' | 'crisis' | 'limit' | 'error';
export type StreamState = 'waiting' | 'streaming' | 'done' | 'restoring' | 'lost';

export const DEAL_MS = 600; // the room opens (--motion-night-open), then the first card turns
export const FLIP_INTERVAL_MS = 900; // one card after another, ≤ 1 s each (--motion-card-flip is 800 ms)

export interface NightState {
  phase: Phase;
  reading: ReadingCreated | null;
  revealed: number;
  answer: Answer;
  softLine: string | null;
  stream: StreamState;
  crisis: CrisisPayload | null;
  error: ErrorKind | null;
  counts: FollowupCounts | null;
  remaining: number | null; // readings left today (from creation; the paid warning uses 402 confirm's number)
  followups: Followup[];
  confirm: { question: string; remaining: number } | null;
  followupError: ErrorKind | null;
  followupPlus: boolean;
}

export const CLOSED: NightState = {
  phase: 'closed', reading: null, revealed: 0, answer: EMPTY_ANSWER, softLine: null, stream: 'waiting', crisis: null,
  error: null, counts: null, remaining: null, followups: [], confirm: null, followupError: null, followupPlus: false,
};

export type NightAction =
  | { type: 'open' }
  | { type: 'created'; reading: ReadingCreated; reducedMotion: boolean }
  | { type: 'crisis'; payload: CrisisPayload }
  | { type: 'failed'; error: ErrorKind }
  | { type: 'flip' }
  | { type: 'stream'; event: SseEvent }
  | { type: 'streamEnded'; outcome: 'done' | 'lost' }
  | { type: 'restoring' }
  | { type: 'restored'; view: ReadingView }
  | { type: 'retrying' }
  | { type: 'counts'; counts: FollowupCounts }
  | { type: 'followupAsk'; question: string }
  | { type: 'followupCancel' }
  | { type: 'followupEvent'; event: SseEvent }
  | { type: 'followupRefused'; question: string; refusal: FollowupRefusal }
  | { type: 'followupRestored'; followup: SavedFollowup }
  | { type: 'followupLost' }
  | { type: 'close' };

function toCrisis(state: NightState, payload: CrisisPayload): NightState {
  // nothing of the reading stays on screen: no cards, no answer, no follow-up text (spec 4.2 hand-off)
  return { ...CLOSED, phase: 'crisis', crisis: payload };
}

function lastFollowup(state: NightState, update: (f: Followup) => Followup): NightState {
  if (state.followups.length === 0) return state;
  const followups = state.followups.slice();
  followups[followups.length - 1] = update(followups[followups.length - 1]);
  return { ...state, followups };
}

export function nightReducer(state: NightState, action: NightAction): NightState {
  switch (action.type) {
    case 'open':
      return { ...CLOSED, phase: 'opening' };
    case 'created': {
      if (state.phase !== 'opening') return state;
      const n = action.reading.cards.length;
      return {
        ...state, phase: 'reading', reading: action.reading, revealed: action.reducedMotion ? n : 0,
        softLine: action.reading.soft_line, remaining: action.reading.remaining, stream: 'waiting',
      };
    }
    case 'crisis':
      return state.phase === 'closed' ? state : toCrisis(state, action.payload);
    case 'failed':
      if (state.phase === 'closed') return state;
      return action.error === 'limit' ? { ...CLOSED, phase: 'limit' } : { ...state, phase: 'error', error: action.error };
    case 'flip':
      if (state.phase !== 'reading' || !state.reading || state.revealed >= state.reading.cards.length) return state;
      return { ...state, revealed: state.revealed + 1 };
    case 'stream': {
      if (state.phase !== 'reading') return state;
      const { event } = action;
      const data = (event.data && typeof event.data === 'object' ? event.data : {}) as Record<string, unknown>;
      if (event.event === 'crisis') return toCrisis(state, data as unknown as CrisisPayload);
      if (event.event === 'meta') { // every stream starts again from nothing: a repeated stream never appends
        const softLine = typeof data.soft_line === 'string' ? data.soft_line : state.softLine;
        return { ...state, softLine, stream: 'streaming', answer: EMPTY_ANSWER };
      }
      if (event.event === 'error') return { ...state, stream: 'lost' };
      const answer = applyAnswerEvent(state.answer, event);
      return { ...state, answer, stream: event.event === 'done' ? 'done' : 'streaming' };
    }
    case 'streamEnded':
      if (state.phase !== 'reading' || state.stream === 'done') return state;
      return { ...state, stream: action.outcome };
    case 'restoring':
      return state.phase === 'reading' ? { ...state, stream: 'restoring' } : state;
    case 'restored': {
      if (state.phase !== 'reading') return state;
      const { view } = action;
      if (view.answer_shown === 'crisis') return toCrisis(state, view as unknown as CrisisPayload);
      return {
        ...state, answer: answerFromView(view), stream: 'done', softLine: view.soft_line ?? state.softLine,
        counts: { followups_left: view.followups_left, followup_attempts_left: view.followup_attempts_left },
      };
    }
    case 'retrying':
      return state.phase === 'reading' ? { ...state, answer: EMPTY_ANSWER, stream: 'waiting' } : state;
    case 'counts':
      return state.phase === 'reading' ? { ...state, counts: action.counts } : state;
    case 'followupAsk':
      if (state.phase !== 'reading') return state;
      return { ...state, confirm: null, followupError: null, followupPlus: false, followups: [...state.followups, newFollowup(action.question)] };
    case 'followupCancel':
      return { ...state, confirm: null };
    case 'followupEvent': {
      if (state.phase !== 'reading' || state.followups.length === 0) return state;
      const update = applyFollowupEvent(state.followups[state.followups.length - 1], action.event);
      if (update.crisis) return toCrisis(state, update.crisis);
      let next = lastFollowup(state, () => update.followup);
      if (update.counts) next = { ...next, counts: update.counts };
      if (action.event.event === 'done' && update.followup.usedReading === true && next.remaining !== null) {
        next = { ...next, remaining: Math.max(next.remaining - 1, 0) };
      }
      return next;
    }
    case 'followupRefused': {
      if (state.phase !== 'reading') return state;
      const { refusal } = action;
      if (refusal.type === 'crisis') return toCrisis(state, refusal.payload);
      const next = { ...state, followups: state.followups.slice(0, -1) }; // nothing was asked
      if (refusal.type === 'confirm') return { ...next, confirm: { question: action.question, remaining: refusal.remaining } };
      if (refusal.type === 'plus') return { ...next, followupPlus: true };
      return { ...next, followupError: refusal.error };
    }
    case 'followupRestored': // the stream broke but the API saved the answer (spec 4.2 §8.11)
      if (state.phase !== 'reading') return state;
      return lastFollowup({ ...state, followupError: null }, (f) => ({
        ...f, text: action.followup.answer ?? '', softLine: action.followup.soft_line, status: 'done',
      }));
    case 'followupLost':
      return lastFollowup({ ...state, followupError: 'network' }, (f) => (f.status === 'streaming' ? { ...f, status: 'failed' } : f));
    case 'close':
      return CLOSED;
  }
}

export function cardsCount(state: NightState): number {
  return state.reading ? state.reading.cards.length : 0;
}

export function allRevealed(state: NightState): boolean {
  return state.phase === 'reading' && state.reading !== null && state.revealed >= state.reading.cards.length;
}

/** The answer is on screen once every card is turned and some text has arrived. */
export function answerVisible(state: NightState): boolean {
  return allRevealed(state) && state.answer.started;
}

/** The whole answer is shown: the moment of the `reading_shown` event. */
export function readingShown(state: NightState): boolean {
  return answerVisible(state) && state.stream === 'done';
}

/** The polite status line (aria-live) for the current moment. */
export function statusKey(state: NightState): DictKey | null {
  if (state.phase === 'opening') return 'shuffling';
  if (state.phase !== 'reading') return null;
  if (state.stream === 'restoring') return 'restoring';
  if (state.stream === 'lost') return 'streamLost';
  if (!allRevealed(state)) return cardsCount(state) === 3 ? 'dealtThree' : 'dealtOne';
  if (!state.answer.started) return 'writing';
  if (state.stream !== 'done') return 'writing';
  const last = state.followups[state.followups.length - 1];
  if (last?.status === 'streaming') return 'writing';
  if (last?.status === 'done' || last?.status === 'replaced') return 'followupReady';
  return 'readingReady';
}

/** Which follow-up the room may offer now: only under a finished model answer, one at a time. */
export function followupNow(state: NightState): Offer {
  if (!readingShown(state) || state.answer.shown !== 'model') return 'none';
  if (state.followups.some((f) => f.status === 'streaming')) return 'none';
  return followupOffer(state.counts);
}

export type RoomEvent = 'night_open' | 'cards_revealed' | 'reading_shown';

/** Analytics events due on a transition (docs/design/analytics-events.md). */
export function transitionEvents(prev: NightState, next: NightState): RoomEvent[] {
  const events: RoomEvent[] = [];
  if (prev.phase !== 'opening' && next.phase === 'opening') events.push('night_open');
  if (!allRevealed(prev) && allRevealed(next)) events.push('cards_revealed');
  if (!readingShown(prev) && readingShown(next)) events.push('reading_shown');
  return events;
}
