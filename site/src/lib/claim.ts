// Saving a guest reading through sign-in (spec 4.4b §4; spec 4.3 §4): the e-mail link and Google come back to the
// diary of the page's language, `?claim=<token>` (one-time token of the reading, so it can be saved from any
// device) and `&remind=1` when "Remind me in 7 days" was ticked. After sign-in the diary calls
// POST /api/account/claim once — only after a sign-in started on this device or with a token in the address
// (api/README.md: on a shared computer a claim without tokens takes every guest reading of the device) — then
// removes `claim` and `remind` from the address bar. This device's guest readings move ("device": true) only after
// a sign-in started here: a link opened on another device moves the reading of its token only (owner decision 12).
// The consent and signup_done need that mark or a reading actually moved: the same address opened again (Back after
// the library cleared #access_token, or a made-up token) switches nothing on (Fable plan review I1).
import type { AccountApi } from './accountApi';
import { analyticsEvent, type AnalyticsEvent } from './analytics';
import { clearSignInStarted, signInStarted, type SignInMethod, type StorageLike } from './authState';
import type { ErrorKind } from './errors';
import { pagePath } from './routes';
import type { Lang } from './types';

export interface ReturnParams {
  claim: string | null;
  remind: boolean;
}

/** Where the e-mail link and Google bring the person back. */
export function returnUrl(origin: string, lang: Lang, params: ReturnParams = { claim: null, remind: false }): string {
  const query = new URLSearchParams();
  if (params.claim) query.set('claim', params.claim);
  if (params.remind) query.set('remind', '1');
  const text = query.toString();
  return `${origin}${pagePath('diary', lang)}${text ? `?${text}` : ''}`;
}

export function readReturnParams(search: string): ReturnParams {
  const query = new URLSearchParams(search);
  const claim = query.get('claim');
  return { claim: claim && claim.length <= 100 ? claim : null, remind: query.get('remind') === '1' };
}

/** The same address without `claim` and `remind` (the entry `r` and anything else stay) and without the hash,
 * where the sign-in library may have left #access_token=… (the diary page has no anchors). */
export function cleanReturnUrl(href: string): string {
  const url = new URL(href);
  url.searchParams.delete('claim');
  url.searchParams.delete('remind');
  return `${url.pathname}${url.search}`;
}

export interface FinishDeps {
  api: Pick<AccountApi, 'claim' | 'setConsent'>;
  storage: StorageLike | null;
  href: string;
  lang: Lang;
  method: (started: SignInMethod | null) => SignInMethod;
  replaceUrl: (url: string) => void;
  send: (event: AnalyticsEvent) => void;
  now?: number;
}

export type FinishResult =
  | { type: 'none' } // nothing to finish: an ordinary visit of a signed-in person
  | { type: 'claimed'; claimed: string[] }
  | { type: 'error'; error: ErrorKind }; // nothing changed: the address keeps its token, the mark stays

let running: Promise<FinishResult> | null = null;

/** After sign-in, once per page: the claim, the reminder consent, `signup_done`, a clean address. */
export function finishSignIn(deps: FinishDeps): Promise<FinishResult> {
  running ??= finish(deps).finally(() => { running = null; });
  return running;
}

async function finish(deps: FinishDeps): Promise<FinishResult> {
  const params = readReturnParams(new URL(deps.href).search);
  const started = signInStarted(deps.now ?? Date.now(), deps.storage);
  if (!params.claim && !started) {
    if (params.remind) deps.replaceUrl(cleanReturnUrl(deps.href));
    return { type: 'none' };
  }
  const result = await deps.api.claim(params.claim ? [params.claim] : [], started !== null);
  if (!result.ok) return { type: 'error', error: result.error };
  const claimed = result.data?.claimed ?? [];
  if (started || claimed.length > 0) {
    if (params.remind) await deps.api.setConsent(true); // a failure here leaves the switch on the account page
    deps.send(analyticsEvent('signup_done', null, deps.lang, { method: deps.method(started) }));
  }
  clearSignInStarted(deps.storage);
  deps.replaceUrl(cleanReturnUrl(deps.href));
  return { type: 'claimed', claimed };
}

/** Supabase sends a failed or expired link back with #error=…&error_code=… in the address. */
export function linkFailed(hash: string): boolean {
  return new URLSearchParams(hash.replace(/^#/, '')).has('error');
}
