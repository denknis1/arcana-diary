// The options the sign-in library is created with (final review M1): it takes a session from the address only on
// the diary pages, where every sign-in comes back. The library itself is replaced: nothing is loaded or fetched.
import { describe, expect, it, vi } from 'vitest';
import { createClient } from './supabaseClient';

const h = vi.hoisted(() => ({ settings: [] as Array<Record<string, unknown>> }));
vi.mock('@supabase/auth-js', () => ({
  AuthClient: class {
    constructor(settings: Record<string, unknown>) {
      h.settings.push(settings);
    }
  },
}));

type Detect = (url: URL, params: Record<string, string>) => boolean;

function detect(): Detect {
  h.settings.length = 0;
  createClient({ enabled: true, supabase_url: 'https://abc.supabase.co', anon_key: 'sb_publishable_x', google: false });
  expect(h.settings).toHaveLength(1);
  const option = h.settings[0].detectSessionInUrl;
  expect(typeof option).toBe('function'); // auth-js 2.119.0 calls it in _isImplicitGrantCallback (GoTrueClient.js:3355-3358)
  return option as Detect;
}

describe('createClient', () => {
  it('is the implicit flow with the site\'s storage key', () => {
    detect();
    expect(h.settings[0]).toMatchObject({
      url: 'https://abc.supabase.co/auth/v1', headers: { apikey: 'sb_publishable_x' }, storageKey: 'ad-auth',
      persistSession: true, autoRefreshToken: true, flowType: 'implicit',
    });
  });

  it('takes a session (or a failed link) from the address on the diary pages only', () => {
    const take = detect();
    const at = (path: string) => new URL(`https://arcana.test${path}`);
    expect(take(at('/diary'), { access_token: 'x', refresh_token: 'y' })).toBe(true);
    expect(take(at('/es/diario'), { access_token: 'x' })).toBe(true);
    expect(take(at('/diary'), { error: 'access_denied', error_code: 'otp_expired' })).toBe(true);
    expect(take(at('/diary'), { error_description: 'Email link is invalid' })).toBe(true);
    expect(take(at('/diary'), {})).toBe(false); // no callback in the address: nothing to take
    for (const path of ['/one-card', '/', '/es', '/account', '/es/cuenta', '/daily', '/diary/x', '/diaryx']) {
      expect(take(at(path), { access_token: 'x', refresh_token: 'y' }), path).toBe(false);
    }
  });
});
