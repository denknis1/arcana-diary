// The only file that imports @supabase/auth-js (the guards test checks it). auth.ts loads it with import(), so
// the library is a chunk of its own that a guest's reading page never downloads (tools/site/check_dist.py).
// Implicit flow: the token comes back in the address (#access_token=…), so the e-mail link can be opened on any
// device (owner decision 14.11.2026); detectSessionInUrl reads it and clears the hash.
import { AuthClient } from '@supabase/auth-js';
import type { AuthClientLike } from './auth';
import type { AuthConfig } from './authConfig';

export const AUTH_STORAGE_KEY = 'ad-auth';

export function createClient(config: AuthConfig): AuthClientLike {
  return new AuthClient({
    url: `${config.supabase_url}/auth/v1`,
    headers: { apikey: config.anon_key },
    storageKey: AUTH_STORAGE_KEY,
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
    flowType: 'implicit',
  }) as unknown as AuthClientLike;
}
