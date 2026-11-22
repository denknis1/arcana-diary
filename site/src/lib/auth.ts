// Signing in through Supabase in the browser (spec 4.4b §3): an e-mail link (implicit flow: the link works on any
// device) and Google, both back to the diary page of the page's language. The library itself lives in
// supabaseClient.ts and is loaded with import() only here, so a guest's reading page never downloads it; only the
// parts of it this site uses are typed below (tests pass a fake client).
import type { AuthConfig } from './authConfig';
import { authConfig } from './authConfig';
import {
  browserStorage, clearLibrarySession, clearSignInStarted, clearSignedIn, markSignedIn, type SignInMethod, type StorageLike,
} from './authState';

export interface SessionLike {
  access_token: string;
  user?: { email?: string | null; app_metadata?: { provider?: string } };
}

export interface AuthErrorLike {
  status?: number;
  code?: string;
  message?: string;
}

type SessionAnswer = Promise<{ data: { session: SessionLike | null }; error: unknown }>;

/** The part of @supabase/auth-js's AuthClient that this site calls. */
export interface AuthClientLike {
  getSession(): SessionAnswer;
  refreshSession(): SessionAnswer;
  signInWithOtp(credentials: { email: string; options: { emailRedirectTo: string; shouldCreateUser: boolean } }):
    Promise<{ error: AuthErrorLike | null }>;
  signInWithOAuth(credentials: { provider: 'google'; options: { redirectTo: string } }):
    Promise<{ error: AuthErrorLike | null }>;
  signOut(options: { scope: 'local' }): Promise<{ error: unknown }>;
}

export type ClientFactory = (config: AuthConfig) => Promise<AuthClientLike>;

/** The real library, as its own chunk (the build checks that reading pages do not load it). */
export const loadSupabaseClient: ClientFactory = async (config) => (await import('./supabaseClient')).createClient(config);

export type SendError = 'tooOften' | 'badEmail' | 'unavailable';
export type SendResult = { ok: true } | { ok: false; error: SendError };

/** Supabase's errors as one readable line each (spec 4.4b §4: "too often", "wrong e-mail"). */
export function sendError(error: AuthErrorLike): SendError {
  const code = error.code ?? '';
  if (error.status === 429 || code.includes('rate_limit')) return 'tooOften';
  // auth-js error codes (error-codes.ts): only these two mean "this address is wrong"; anything else is unavailable
  if (code === 'email_address_invalid' || (code === 'validation_failed' && /e-?mail/i.test(error.message ?? ''))) {
    return 'badEmail';
  }
  return 'unavailable';
}

/** What the library says about this device: a session; a clean "no session" (it answered, nothing there); or
 * "unavailable" — it answered an error with no session, or did not load: not "signed out", try again later. */
export type SessionCheck =
  | { type: 'session'; session: SessionLike }
  | { type: 'none' }
  | { type: 'unavailable' };

export interface Auth {
  /** The three answers apart; keeps the `ad_signed_in` flag in step (cleared only on `none`). */
  check(): Promise<SessionCheck>;
  /** The current session, or null (`none` and `unavailable` alike); keeps the `ad_signed_in` flag in step with it. */
  session(): Promise<SessionLike | null>;
  token(): Promise<string | null>;
  /** One refresh after 401 {"reason": "auth"}; null when it did not help. */
  refresh(): Promise<string | null>;
  sendLink(email: string, redirectTo: string): Promise<SendResult>;
  google(redirectTo: string): Promise<SendResult>;
  /** This device only: the library's session, `ad_signed_in` and the started mark go. */
  signOut(): Promise<void>;
}

export function createAuth(config: AuthConfig, factory: ClientFactory = loadSupabaseClient,
  storage: StorageLike | null = browserStorage()): Auth {
  let client: Promise<AuthClientLike> | null = null;
  // a failed load (offline, a chunk that did not arrive) is not kept: the next use tries again (review M7)
  const lib = () => (client ??= factory(config).catch((error: unknown) => {
    client = null;
    throw error;
  }));

  // a library error with no session (offline refresh, say) is not "signed out": the flag stays, no token this time
  const keep = (current: SessionLike | null, error: unknown = null) => {
    if (current?.access_token) markSignedIn(storage);
    else if (!error) clearSignedIn(storage);
    return current?.access_token ? current : null;
  };

  const sent = async (answer: Promise<{ error: AuthErrorLike | null }>): Promise<SendResult> => {
    try {
      const { error } = await answer;
      return error ? { ok: false, error: sendError(error) } : { ok: true };
    } catch {
      return { ok: false, error: 'unavailable' };
    }
  };

  return {
    async check() {
      try {
        const { data, error } = await (await lib()).getSession();
        const current = keep(data.session, error);
        if (current) return { type: 'session', session: current };
        return error ? { type: 'unavailable' } : { type: 'none' };
      } catch {
        return { type: 'unavailable' }; // the library did not load (or threw): no answer, the flag stays
      }
    },
    async session() {
      const answer = await this.check();
      return answer.type === 'session' ? answer.session : null;
    },
    async token() {
      return (await this.session())?.access_token ?? null;
    },
    async refresh() {
      try {
        const { data, error } = await (await lib()).refreshSession();
        return keep(data.session, error)?.access_token ?? null;
      } catch {
        return null;
      }
    },
    async sendLink(email, redirectTo) {
      return sent(lib().then((c) => c.signInWithOtp({ email, options: { emailRedirectTo: redirectTo, shouldCreateUser: true } })));
    },
    async google(redirectTo) {
      return sent(lib().then((c) => c.signInWithOAuth({ provider: 'google', options: { redirectTo } })));
    },
    async signOut() {
      clearSignedIn(storage); // first: this device is a guest at once, even if the library fails or hangs (review M6)
      clearSignInStarted(storage);
      clearLibrarySession(storage); // the library's own keys too, in case it cannot load below
      try {
        await (await lib()).signOut({ scope: 'local' }); // auth-js 2.119 drops the local session before its request
      } catch {
        // nothing more to undo here
      }
    },
  };
}

/** How the session was made, for `signup_done`: the started mark, else what the library says. */
export function methodOf(current: SessionLike | null, started: SignInMethod | null): SignInMethod {
  if (started) return started;
  return current?.user?.app_metadata?.provider === 'google' ? 'google' : 'email';
}

let shared: Auth | null = null;

/** The page's one Auth for these settings (one library client per page). */
export function sharedAuth(config: AuthConfig): Auth {
  shared ??= createAuth(config);
  return shared;
}

/** The page's Auth, or null when sign-in is off or its settings cannot be read. */
export async function getAuth(): Promise<Auth | null> {
  const config = await authConfig();
  return config && config.enabled ? sharedAuth(config) : null;
}

export type SessionStatus =
  | { type: 'off' } // no SUPABASE_URL / SUPABASE_ANON_KEY: "sign-in opens soon"
  // the settings could not be read, or the library errored with no session or did not load: "try again later";
  // never "signed out" — `ad_signed_in` stays
  | { type: 'unreachable' }
  | { type: 'signedOut'; auth: Auth; google: boolean } // a clean "no session": the flag is already cleared
  | { type: 'signedIn'; auth: Auth; google: boolean; session: SessionLike };

/** What the diary and the account page start from (spec 4.4b §5, §6). */
export async function openSession(readConfig: () => Promise<AuthConfig | null> = authConfig,
  makeAuth: (config: AuthConfig) => Auth = sharedAuth): Promise<SessionStatus> {
  const config = await readConfig();
  if (config === null) return { type: 'unreachable' };
  if (!config.enabled) return { type: 'off' };
  const auth = makeAuth(config);
  const answer = await auth.check();
  if (answer.type === 'unavailable') return { type: 'unreachable' };
  return answer.type === 'session' ? { type: 'signedIn', auth, google: config.google, session: answer.session }
    : { type: 'signedOut', auth, google: config.google };
}

/** Tests only: the next call builds a new Auth. */
export function forgetAuth(): void {
  shared = null;
}
