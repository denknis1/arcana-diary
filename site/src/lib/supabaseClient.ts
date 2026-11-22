// The only file that imports @supabase/auth-js (the guards test checks it). auth.ts loads it with import(), so
// the library is a chunk of its own that a guest's reading page never downloads (tools/site/check_dist.py).
// Implicit flow: the token comes back in the address (#access_token=…), so the e-mail link can be opened on any
// device (owner decision 14.11.2026); detectSessionInUrl reads it and clears the hash — on the diary pages only,
// where every sign-in comes back (claim.ts returnUrl): a `#access_token=…&refresh_token=…` stuck on another page
// (a reading page, the account) never swaps the person's session for someone else's (final review M1).
import { AuthClient } from '@supabase/auth-js';
import type { AuthClientLike } from './auth';
import type { AuthConfig } from './authConfig';
import { AUTH_STORAGE_KEY } from './authState';
import { pagePath } from './routes';

const SIGN_IN_RETURNS: readonly string[] = [pagePath('diary', 'en'), pagePath('diary', 'es')];

/** auth-js 2.119.0 accepts a function for `detectSessionInUrl` and calls it in place of its own check
 * (`_isImplicitGrantCallback`, GoTrueClient.js:3355-3358; type in lib/types.d.ts:58). So: the library's own test
 * (GoTrueClient.js:3359), and only on the diary pages. */
function sessionInUrl(url: URL, params: Record<string, string>): boolean {
  if (!SIGN_IN_RETURNS.includes(url.pathname)) return false;
  return Boolean(params.access_token || params.error || params.error_description || params.error_code);
}

export function createClient(config: AuthConfig): AuthClientLike {
  return new AuthClient({
    url: `${config.supabase_url}/auth/v1`,
    headers: { apikey: config.anon_key },
    storageKey: AUTH_STORAGE_KEY,
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: sessionInUrl,
    flowType: 'implicit',
  }) as unknown as AuthClientLike;
}
