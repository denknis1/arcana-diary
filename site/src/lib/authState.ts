// What this device remembers about signing in (spec 4.4b §3, §4), apart from the session the sign-in library keeps:
// `ad_signed_in` — there is a session here, so API requests load the library and carry the token; `ad_signin_started`
// — a sign-in was started by a button on this device (e-mail link sent, or Google), so the diary may move this
// device's guest readings into the account once (api/README.md "Передача в 4.4"). Never a token, never an e-mail.

export const SIGNED_IN_KEY = 'ad_signed_in';
export const STARTED_KEY = 'ad_signin_started';
/** An e-mail link opened later than this is not "started here" any more (the link itself lives an hour). */
export const STARTED_MAX_AGE_MS = 24 * 60 * 60 * 1000;

export type SignInMethod = 'email' | 'google';

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/** localStorage, or null where it cannot be used (private mode, blocked): then the site works as a guest. */
export function browserStorage(): StorageLike | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage;
  } catch {
    return null;
  }
}

function safely<T>(fallback: T, action: () => T): T {
  try {
    return action();
  } catch {
    return fallback;
  }
}

export function isSignedIn(storage: StorageLike | null = browserStorage()): boolean {
  return safely(false, () => storage?.getItem(SIGNED_IN_KEY) === '1');
}

export function markSignedIn(storage: StorageLike | null = browserStorage()): void {
  safely(undefined, () => storage?.setItem(SIGNED_IN_KEY, '1'));
}

export function clearSignedIn(storage: StorageLike | null = browserStorage()): void {
  safely(undefined, () => storage?.removeItem(SIGNED_IN_KEY));
}

export function markSignInStarted(method: SignInMethod, now: number = Date.now(),
  storage: StorageLike | null = browserStorage()): void {
  safely(undefined, () => storage?.setItem(STARTED_KEY, JSON.stringify({ method, at: now })));
}

/** The method of a sign-in started on this device within STARTED_MAX_AGE_MS, or null. */
export function signInStarted(now: number = Date.now(), storage: StorageLike | null = browserStorage()): SignInMethod | null {
  return safely(null, () => {
    const raw = storage?.getItem(STARTED_KEY);
    if (!raw) return null;
    const mark = JSON.parse(raw) as { method?: unknown; at?: unknown };
    const fresh = typeof mark.at === 'number' && now - mark.at >= 0 && now - mark.at <= STARTED_MAX_AGE_MS;
    return fresh && (mark.method === 'email' || mark.method === 'google') ? mark.method : null;
  });
}

export function clearSignInStarted(storage: StorageLike | null = browserStorage()): void {
  safely(undefined, () => storage?.removeItem(STARTED_KEY));
}
