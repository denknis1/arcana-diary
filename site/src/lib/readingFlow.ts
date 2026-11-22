// The requests behind the night room (spec 4.4a §4): create → (403 turnstile → token → create again) → stream;
// a broken stream is restored with GET /api/readings/{id} (wait while it is still being written, stream again if
// nobody is writing); POST /retry only after a fallback answer; follow-ups stream the same way and a broken one
// is read back from GET /api/readings/{id} too (the API keeps writing it, spec 4.2 §8.11). Spec 4.5 §5: every press
// of Draw and every follow-up sent carries a new request_id; a request that got no answer at all is sent once more
// with the same number (the API gives back what it already made), then the usual restore follows.
import type { Api } from './api';
import { followupBody, type FollowupBody, type FollowupRefusal } from './followups';
import type { NightAction } from './nightRoom';
import type { SseEvent } from './sse';
import type { CreateBody, FollowupCounts } from './types';

export interface FlowDeps {
  api: Api;
  dispatch: (action: NightAction) => void;
  turnstileToken: (sitekey: string) => Promise<string | null>;
  sleep: (ms: number) => Promise<void>;
  reducedMotion: boolean;
  newId: () => string; // a request number (requestId.ts)
}

export const RESTORE_TRIES = 10;
export const RESTORE_WAIT_MS = 2000;
/** Before the one automatic repeat of a request that got no answer: an instant repeat would fail the same way. */
export const REPEAT_WAIT_MS = 1000;
/** What a new reading allows (two free follow-ups, eight attempts); used only when the counts cannot be read —
 * the API still refuses what is not allowed (402 / 429). */
export const DEFAULT_COUNTS: FollowupCounts = { followups_left: 2, followup_attempts_left: 8 };

/** POST /api/readings; when it got no answer at all, once more a second later with the same body and request_id. */
async function create(deps: FlowDeps, body: CreateBody) {
  const result = await deps.api.createReading(body);
  if (result.type !== 'error' || result.error !== 'network') return result;
  await deps.sleep(REPEAT_WAIT_MS);
  return deps.api.createReading(body);
}

export async function startReading(deps: FlowDeps, draw: CreateBody): Promise<void> {
  const body: CreateBody = { ...draw, request_id: deps.newId() }; // one number for this press of Draw
  let result = await create(deps, body);
  if (result.type === 'error' && result.error === 'turnstile') {
    const sitekey = typeof result.body?.sitekey === 'string' ? result.body.sitekey : '';
    if (!sitekey) { // no key to run the check with: the room shows "unavailable" with the help link
      deps.dispatch({ type: 'failed', error: 'unavailable' });
      return;
    }
    const token = await deps.turnstileToken(sitekey);
    if (token) result = await create(deps, { ...body, turnstile_token: token });
  }
  if (result.type === 'crisis') {
    deps.dispatch({ type: 'crisis', payload: result.payload });
    return;
  }
  if (result.type === 'error') {
    deps.dispatch({ type: 'failed', error: result.error });
    return;
  }
  deps.dispatch({ type: 'created', reading: result.reading, reducedMotion: deps.reducedMotion });
  await streamReading(deps, result.reading.id, body.tz, 'stream');
}

export async function streamReading(deps: FlowDeps, id: string, tz: string | undefined, mode: 'stream' | 'retry',
  restoreOnLoss = true): Promise<void> {
  if (mode === 'retry') deps.dispatch({ type: 'retrying' });
  let done = false;
  let crisis = false;
  let failed = false;
  const onEvent = (event: { event: string; data: unknown }) => {
    if (event.event === 'done') done = true;
    if (event.event === 'crisis') crisis = true;
    if (event.event === 'error') failed = true;
    deps.dispatch({ type: 'stream', event });
  };
  const end = mode === 'stream' ? await deps.api.streamReading(id, tz, onEvent) : await deps.api.retryReading(id, tz, onEvent);
  if (end.type === 'error') {
    if (mode === 'retry' && restoreOnLoss) await restoreReading(deps, id, tz); // a refused retry keeps the saved answer
    else if (mode === 'stream' && restoreOnLoss && (end.error === 'unavailable' || end.error === 'network')) {
      await restoreReading(deps, id, tz); // the reading is created and counted, the API keeps writing it
    } else deps.dispatch({ type: 'failed', error: end.error });
    return;
  }
  if (crisis) return;
  if (done && !failed) {
    deps.dispatch({ type: 'streamEnded', outcome: 'done' });
    await loadCounts(deps, id, tz);
    return;
  }
  deps.dispatch({ type: 'streamEnded', outcome: 'lost' });
  if (restoreOnLoss) await restoreReading(deps, id, tz);
}

/** After a broken stream: the API keeps writing the answer (spec 4.2 §8.11), so read it back. */
export async function restoreReading(deps: FlowDeps, id: string, tz: string | undefined): Promise<void> {
  deps.dispatch({ type: 'restoring' });
  for (let attempt = 0; attempt < RESTORE_TRIES; attempt++) {
    const result = await deps.api.getReading(id, tz);
    if (result.ok && result.data.status === 'done') {
      deps.dispatch({ type: 'restored', view: result.data });
      return;
    }
    if (result.ok && result.data.status === 'pending') {
      await streamReading(deps, id, tz, 'stream', false);
      return;
    }
    if (!result.ok && result.error === 'gone') {
      deps.dispatch({ type: 'failed', error: 'gone' });
      return;
    }
    await deps.sleep(RESTORE_WAIT_MS);
  }
  deps.dispatch({ type: 'streamEnded', outcome: 'lost' });
}

export async function loadCounts(deps: FlowDeps, id: string, tz: string | undefined): Promise<void> {
  for (let attempt = 0; attempt < 2; attempt++) {
    const result = await deps.api.getReading(id, tz);
    if (result.ok) {
      deps.dispatch({ type: 'counts', counts: {
        followups_left: result.data.followups_left, followup_attempts_left: result.data.followup_attempts_left,
      } });
      return;
    }
    if (attempt === 0) await deps.sleep(RESTORE_WAIT_MS);
  }
  deps.dispatch({ type: 'counts', counts: DEFAULT_COUNTS });
}

/** A follow-up stream broke: read the answer the API saved (it is listed once it is complete). `answeredBefore` is
 * how many answered follow-ups the room knew before the request; a restored answer counts only when the API
 * lists more than that (never matched by question text: the same question may be asked twice).
 * `n` is the follow-up number from the stream's `meta` event, when it arrived: then only the saved follow-up with
 * exactly that `n` counts (a newer-but-other one never does); without it the `answeredBefore` rule is the fallback. */
export async function restoreFollowup(deps: FlowDeps, id: string, answeredBefore: number, tz: string | undefined,
  n?: number, repost?: () => Promise<{ ended: boolean; n?: number }>, body?: FollowupBody): Promise<void> {
  let gone = false;
  for (let attempt = 0; attempt < RESTORE_TRIES; attempt++) {
    const result = await deps.api.getReading(id, tz);
    if (result.ok) {
      const list = result.data.followups ?? [];
      const saved = n !== undefined ? list.find((f) => f.n === n)
        : list.length > answeredBefore ? list[list.length - 1] : undefined;
      if (saved && saved.answer) {
        deps.dispatch({ type: 'followupRestored', followup: saved });
        deps.dispatch({ type: 'counts', counts: {
          followups_left: result.data.followups_left, followup_attempts_left: result.data.followup_attempts_left,
        } });
        return;
      }
    } else if (result.error === 'gone') {
      gone = true;
      break;
    }
    await deps.sleep(RESTORE_WAIT_MS);
  }
  // Stage 4.5 A1: GET never lists a crisis tombstone, so ask once more with the same request_id and body; the API
  // replays the saved answer or the crisis, or says in_progress (then the follow-up stays lost, as before).
  if (repost && !gone) {
    deps.dispatch({ type: 'followupLost', n, answeredBefore, body }); // clears the partial text, then shows it as streaming again
    deps.dispatch({ type: 'followupRetrying' });
    const got = await repost();
    if (got.ended) return;
    n = n ?? got.n; // no number from the first stream: the one the re-POST's meta named, for "Try again"
  }
  deps.dispatch({ type: 'followupLost', n, answeredBefore, body });
  await loadCounts(deps, id, tz);
}

/** A 5xx refusal (unavailable / other): nothing is known about the follow-up, so it is not "refused". */
function isServerError(refusal: FollowupRefusal): boolean {
  return refusal.type === 'error' && (refusal.error === 'unavailable' || refusal.error === 'other');
}

/** "Try again" on a lost follow-up. With a request_id: the same body again (never a new number, never another
 * `use_reading`), so the API replays the saved answer or the crisis tombstone, says in_progress, or (if nothing was
 * saved) answers it as one ask; the result is handled as in `askFollowup`. in_progress or no answer: the GET
 * read-back, with the same `n` and `answeredBefore`. A follow-up without a number: the GET read-back only. */
export async function retryFollowup(deps: FlowDeps, id: string, tz: string | undefined,
  lost: { n?: number; answeredBefore: number; body?: FollowupBody }): Promise<void> {
  deps.dispatch({ type: 'followupRetrying' });
  const body = lost.body;
  let n = lost.n;
  if (body?.request_id) {
    let done = false;
    let crisis = false;
    const result = await deps.api.postFollowup(id, body, (event) => {
      if (event.event === 'done') done = true;
      if (event.event === 'crisis') crisis = true;
      if (event.event === 'meta') {
        const num = (event.data as { followup?: unknown } | null)?.followup;
        if (typeof num === 'number') n = num;
      }
      deps.dispatch({ type: 'followupEvent', event });
    });
    if (result.type === 'refused' && !isServerError(result.refusal)) { // crisis / 402 / 429 / 409 come back as JSON, as for a fresh ask
      deps.dispatch({ type: 'followupRefused', question: body.question, refusal: result.refusal });
      return;
    }
    // a 5xx refusal: the state under this number is unknown, so the follow-up stays lost with its body and its button
    if (result.type !== 'refused' && (crisis || done)) return;
  }
  await restoreFollowup(deps, id, lost.answeredBefore, tz, n, undefined, body);
}

export async function askFollowup(deps: FlowDeps, id: string, question: string, tz: string | undefined,
  useReading: boolean, answeredBefore: number): Promise<void> {
  deps.dispatch({ type: 'followupAsk', question });
  let done = false;
  let crisis = false;
  let n: number | undefined;
  const body = followupBody(question, tz, useReading, deps.newId()); // one number for this follow-up
  const onEvent = (event: SseEvent) => {
    if (event.event === 'done') done = true;
    if (event.event === 'crisis') crisis = true; // the API keeps a tombstone for a reader crisis, GET never lists it: nothing to restore
    if (event.event === 'meta') {
      const num = (event.data as { followup?: unknown } | null)?.followup;
      if (typeof num === 'number') n = num;
    }
    deps.dispatch({ type: 'followupEvent', event });
  };
  let result = await deps.api.postFollowup(id, body, onEvent);
  if (result.type === 'noResponse') { // once more, a second later, with the same number
    await deps.sleep(REPEAT_WAIT_MS);
    result = await deps.api.postFollowup(id, body, onEvent);
  }
  if (result.type === 'refused') {
    deps.dispatch({ type: 'followupRefused', question, refusal: result.refusal });
    return;
  }
  if (crisis) return;
  if (!done) { // broken request or stream, or no `done`
    let reposted = false;
    const repost = async () => { // A1: at most one, same body (same request_id), only after the GET restore found nothing
      if (reposted) return { ended: false, n };
      reposted = true;
      done = false;
      crisis = false;
      const r = await deps.api.postFollowup(id, body, onEvent);
      if (r.type === 'refused' && !isServerError(r.refusal)) { // a fresh ask to the API: crisis / 402 / 429 / 409 come back as JSON
        deps.dispatch({ type: 'followupRefused', question, refusal: r.refusal });
        return { ended: true, n };
      }
      return { ended: r.type !== 'refused' && (done || crisis), n }; // a 5xx refusal: stays lost, restorable
    };
    await restoreFollowup(deps, id, answeredBefore, tz, n, repost, body);
  }
}
