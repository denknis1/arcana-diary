// What a failed API answer means for the screen (spec 4.4a §4, api/README.md "Передача в 4.4").
import type { DictKey } from '../i18n';

export type ErrorKind =
  | 'limit' // 429 {"reason": "limit"}: today's free readings are used — the Plus card (screen 11a)
  | 'busy' // 429 burst or rate: wait a minute
  | 'daycap' // 429 {"reason": "ip_limit"}: this address's cap for the day — try again tomorrow
  | 'attempts' // 429 {"reason": "attempts"}: this reading takes no more follow-ups
  | 'turnstile' // 403 {"reason": "turnstile"}: run the invisible Turnstile check and repeat the request
  | 'unavailable' // 503 (database, model budget, sign-in keys) and 502 / 504 (the API restarts, e.g. a deploy)
  | 'stage' // 401 without a JSON reason: the stage cookie is stale — reload the page
  | 'gone' // 404: the reading expired or is not ours
  | 'network' // no answer at all
  | 'other';

export function reasonOf(body: unknown): string | undefined {
  if (body && typeof body === 'object' && 'reason' in body) {
    const reason = (body as { reason: unknown }).reason;
    return typeof reason === 'string' ? reason : undefined;
  }
  return undefined;
}

export function classifyError(status: number, body: unknown): ErrorKind {
  const reason = reasonOf(body);
  if (status === 0) return 'network';
  if (status === 429) {
    if (reason === 'limit') return 'limit';
    if (reason === 'ip_limit') return 'daycap';
    return reason === 'attempts' ? 'attempts' : 'busy';
  }
  if (status === 403 && reason === 'turnstile') return 'turnstile';
  if (status === 502 || status === 503 || status === 504) return 'unavailable';
  if (status === 401 && reason === undefined) return 'stage';
  if (status === 404) return 'gone';
  return 'other';
}

/** §10.8 of spec 4.2: the 429, 403 and 503 messages also link to help lines. */
export function needsHelpLink(kind: ErrorKind): boolean {
  return kind === 'limit' || kind === 'busy' || kind === 'daycap' || kind === 'attempts' || kind === 'turnstile'
    || kind === 'unavailable';
}

const MESSAGES: Record<ErrorKind, DictKey> = {
  limit: 'plusTitle',
  busy: 'errBusy',
  daycap: 'errDayCap',
  attempts: 'followupNone',
  turnstile: 'errTurnstile',
  unavailable: 'errUnavailable',
  stage: 'errStage',
  gone: 'errGone',
  network: 'errNetwork',
  other: 'errOther',
};

export function errorMessageKey(kind: ErrorKind): DictKey {
  return MESSAGES[kind];
}
