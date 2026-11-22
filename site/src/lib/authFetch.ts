// Every /api/* request of a signed-in person carries Authorization: Bearer (spec 4.4b §3, api/README.md
// "Передача в 4.4"): 401 {"reason": "auth"} — refresh the token once and repeat; still 401 — sign out on this
// device and repeat as a guest. Other answers (401 "sign_in", 401 without JSON on the stage, 503) go back to the
// caller unchanged. A guest (no `ad_signed_in`) never loads the sign-in library: the request goes as it is.
import type { FetchFn } from './api';
import { reasonOf } from './errors';
import type { Auth } from './auth';
import { isSignedIn, type StorageLike, browserStorage } from './authState';

export type AuthSource = () => Promise<Pick<Auth, 'token' | 'refresh' | 'signOut'> | null>;

function withBearer(init: RequestInit | undefined, token: string): RequestInit {
  return { ...init, headers: { ...((init?.headers ?? {}) as Record<string, string>), authorization: `Bearer ${token}` } };
}

async function isAuthRefusal(response: Response): Promise<boolean> {
  if (response.status !== 401) return false;
  try {
    return reasonOf(await response.clone().json()) === 'auth';
  } catch {
    return false; // 401 without JSON: the stage cookie, not the token
  }
}

export function authFetch(base: FetchFn, source: AuthSource, storage: StorageLike | null = browserStorage()): FetchFn {
  return async (input, init) => {
    if (!input.startsWith('/api/') || !isSignedIn(storage)) return base(input, init);
    const auth = await source();
    const token = auth ? await auth.token() : null;
    if (!auth || !token) return base(input, init); // the session went: a guest request
    const first = await base(input, withBearer(init, token));
    if (!(await isAuthRefusal(first))) return first;
    const fresh = await auth.refresh();
    if (fresh) {
      const again = await base(input, withBearer(init, fresh));
      if (!(await isAuthRefusal(again))) return again;
    }
    await auth.signOut();
    return base(input, init);
  };
}
