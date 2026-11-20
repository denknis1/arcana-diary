// The requests behind the night room (spec 4.4a §4): create → (403 turnstile → token → create again) → stream;
// a broken stream is restored with GET /api/readings/{id} (wait while it is still being written, stream again if
// nobody is writing); POST /retry only after a fallback answer; follow-ups stream the same way and a broken one
// is read back from GET /api/readings/{id} too (the API keeps writing it, spec 4.2 §8.11).
import type { Api } from './api';
import { followupBody } from './followups';
import type { NightAction } from './nightRoom';
import type { CreateBody, FollowupCounts } from './types';

export interface FlowDeps {
  api: Api;
  dispatch: (action: NightAction) => void;
  turnstileToken: (sitekey: string) => Promise<string | null>;
  sleep: (ms: number) => Promise<void>;
  reducedMotion: boolean;
}

export const RESTORE_TRIES = 10;
export const RESTORE_WAIT_MS = 2000;
/** What a new reading allows (two free follow-ups, eight attempts); used only when the counts cannot be read —
 * the API still refuses what is not allowed (402 / 429). */
export const DEFAULT_COUNTS: FollowupCounts = { followups_left: 2, followup_attempts_left: 8 };

export async function startReading(deps: FlowDeps, body: CreateBody): Promise<void> {
  let result = await deps.api.createReading(body);
  if (result.type === 'error' && result.error === 'turnstile') {
    const sitekey = typeof result.body?.sitekey === 'string' ? result.body.sitekey : '';
    if (!sitekey) { // no key to run the check with: the room shows "unavailable" with the help link
      deps.dispatch({ type: 'failed', error: 'unavailable' });
      return;
    }
    const token = await deps.turnstileToken(sitekey);
    if (token) result = await deps.api.createReading({ ...body, turnstile_token: token });
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
  n?: number): Promise<void> {
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
      break;
    }
    await deps.sleep(RESTORE_WAIT_MS);
  }
  deps.dispatch({ type: 'followupLost', n, answeredBefore });
  await loadCounts(deps, id, tz);
}

/** "Try again" on a lost follow-up: the same GET read-back with the same `n` and `answeredBefore`, never a new POST
 * (the API may have answered it and, if paid, kept the reading). */
export async function retryFollowup(deps: FlowDeps, id: string, tz: string | undefined,
  lost: { n?: number; answeredBefore: number }): Promise<void> {
  deps.dispatch({ type: 'followupRetrying' });
  await restoreFollowup(deps, id, lost.answeredBefore, tz, lost.n);
}

export async function askFollowup(deps: FlowDeps, id: string, question: string, tz: string | undefined,
  useReading: boolean, answeredBefore: number): Promise<void> {
  deps.dispatch({ type: 'followupAsk', question });
  let done = false;
  let crisis = false;
  let n: number | undefined;
  const result = await deps.api.postFollowup(id, followupBody(question, tz, useReading), (event) => {
    if (event.event === 'done') done = true;
    if (event.event === 'crisis') crisis = true; // the API deletes that follow-up: nothing to restore
    if (event.event === 'meta') {
      const num = (event.data as { followup?: unknown } | null)?.followup;
      if (typeof num === 'number') n = num;
    }
    deps.dispatch({ type: 'followupEvent', event });
  });
  if (result.type === 'refused') {
    deps.dispatch({ type: 'followupRefused', question, refusal: result.refusal });
    return;
  }
  if (crisis) return;
  if (!done) await restoreFollowup(deps, id, answeredBefore, tz, n); // broken request or stream, or no `done`
}
