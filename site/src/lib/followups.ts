// Follow-up questions (spec 4.2 §10.1, api/README.md): two free per reading; after them each one uses a reading
// of today's limit, offered only when followups_left == 0 and followup_attempts_left > 0, first with a warning
// ("this will use 1 reading"), then sent again with use_reading: true. 402 confirm / 402 plus / done.used_reading.
import { classifyError, reasonOf, type ErrorKind } from './errors';
import type { SseEvent } from './sse';
import type { CrisisPayload, FollowupCounts } from './types';

export type Offer = 'free' | 'paid' | 'none';

export function followupOffer(counts: FollowupCounts | null): Offer {
  if (!counts || counts.followup_attempts_left <= 0) return 'none';
  return counts.followups_left > 0 ? 'free' : 'paid';
}

export interface FollowupBody {
  question: string;
  tz?: string;
  use_reading: boolean;
  request_id?: string; // spec 4.5 §5: one number per follow-up sent, the same on its one automatic repeat
}

/** The same tz as the reading was created with (api/README.md: otherwise the day is UTC). */
export function followupBody(question: string, tz: string | undefined, useReading: boolean, requestId?: string): FollowupBody {
  const body: FollowupBody = tz ? { question: question.trim(), tz, use_reading: useReading } : { question: question.trim(), use_reading: useReading };
  if (requestId) body.request_id = requestId;
  return body;
}

export type FollowupRefusal =
  | { type: 'confirm'; remaining: number }
  | { type: 'plus' }
  | { type: 'crisis'; payload: CrisisPayload }
  | { type: 'error'; error: ErrorKind };

/** A follow-up answered with JSON instead of a stream. */
export function followupRefusal(status: number, body: unknown): FollowupRefusal {
  const reason = reasonOf(body);
  if (status === 402 && reason === 'confirm') {
    const remaining = (body as { remaining?: unknown }).remaining;
    return { type: 'confirm', remaining: typeof remaining === 'number' ? remaining : 0 };
  }
  if (status === 402) return { type: 'plus' };
  if (status === 200 && body && typeof body === 'object' && (body as { group?: unknown }).group === 'crisis') {
    return { type: 'crisis', payload: body as CrisisPayload };
  }
  return { type: 'error', error: classifyError(status, body) };
}

export interface Followup {
  question: string;
  text: string;
  status: 'streaming' | 'done' | 'replaced' | 'failed';
  softLine: string | null;
  usedReading: boolean | null;
  /** set when the answer could not be read back in time: the GET-based restore may be run again (never a new POST) */
  lost?: { n?: number; answeredBefore: number };
}

export function newFollowup(question: string): Followup {
  return { question: question.trim(), text: '', status: 'streaming', softLine: null, usedReading: null };
}

export interface FollowupUpdate {
  followup: Followup;
  counts?: FollowupCounts;
  crisis?: CrisisPayload;
}

function sectionText(data: Record<string, unknown>): string {
  const sections = data.sections as Record<string, unknown> | undefined;
  return typeof sections?.followup === 'string' ? sections.followup : '';
}

export function applyFollowupEvent(followup: Followup, event: SseEvent): FollowupUpdate {
  const data = (event.data && typeof event.data === 'object' ? event.data : {}) as Record<string, unknown>;
  switch (event.event) {
    case 'meta':
      return { followup: { ...followup, softLine: typeof data.soft_line === 'string' ? data.soft_line : null } };
    case 'text':
      return typeof data.text === 'string' ? { followup: { ...followup, text: followup.text + data.text } } : { followup };
    case 'replace':
      return { followup: { ...followup, text: sectionText(data), status: 'replaced' } };
    case 'fallback':
      return { followup: { ...followup, text: sectionText(data), status: 'failed' } };
    case 'crisis': // the shown text is cleared; the room shows the crisis answer instead
      return { followup: { ...followup, text: '', status: 'failed' }, crisis: data as unknown as CrisisPayload };
    case 'error': // "in_progress": a repeat of a follow-up the API is still writing — it is read back, still streaming
      return data.reason === 'in_progress' ? { followup } : { followup: { ...followup, status: 'failed' } };
    case 'done': {
      const update: FollowupUpdate = {
        followup: {
          ...followup,
          status: data.answer_shown === 'model' ? 'done' : followup.status === 'streaming' ? 'failed' : followup.status,
          usedReading: typeof data.used_reading === 'boolean' ? data.used_reading : null,
        },
      };
      if (typeof data.followups_left === 'number' && typeof data.followup_attempts_left === 'number') {
        update.counts = { followups_left: data.followups_left, followup_attempts_left: data.followup_attempts_left };
      }
      return update;
    }
    default:
      return { followup };
  }
}
