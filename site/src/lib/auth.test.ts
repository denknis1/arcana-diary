import { describe, expect, it } from 'vitest';
import { createAuth, methodOf, openSession, sendError, type SessionLike } from './auth';
import type { AuthConfig } from './authConfig';
import { AUTH_STORAGE_KEY, STARTED_KEY, SIGNED_IN_KEY, markSignInStarted } from './authState';
import { fakeClient, memoryStorage, session } from './testing/auth';

const CONFIG: AuthConfig = { enabled: true, supabase_url: 'https://abc.supabase.co', anon_key: 'sb_publishable_x', google: true };

function setup(current: SessionLike | null = session()) { // typed: setup(null) is a signed-out client
  const client = fakeClient(current);
  const storage = memoryStorage();
  let loads = 0;
  const auth = createAuth(CONFIG, async (config) => {
    loads += 1;
    expect(config).toEqual(CONFIG);
    return client;
  }, storage);
  return { auth, client, storage, loads: () => loads };
}

describe('createAuth', () => {
  it('loads the library once, on first use, and keeps the signed-in flag in step with the session', async () => {
    const { auth, client, storage, loads } = setup();
    expect(loads()).toBe(0);
    expect(await auth.token()).toBe('tok-1');
    expect(await auth.token()).toBe('tok-1');
    expect(loads()).toBe(1);
    expect(storage.data[SIGNED_IN_KEY]).toBe('1');
    client.session = null; // signed out in another tab
    expect(await auth.token()).toBeNull();
    expect(storage.data[SIGNED_IN_KEY]).toBeUndefined();
  });

  it('refreshes once and gives the new token, or null', async () => {
    const { auth, client } = setup();
    client.refreshed = session('tok-2');
    expect(await auth.refresh()).toBe('tok-2');
    client.refreshed = null;
    expect(await auth.refresh()).toBeNull();
  });

  it('sends the e-mail link back to the given address (implicit flow is set in supabaseClient.ts)', async () => {
    const { auth, client } = setup(null);
    expect(await auth.sendLink('ana@example.com', 'https://arcana.test/diary?claim=t')).toEqual({ ok: true });
    expect(client.calls.at(-1)).toEqual({ method: 'signInWithOtp', args: {
      email: 'ana@example.com', options: { emailRedirectTo: 'https://arcana.test/diary?claim=t', shouldCreateUser: true },
    } });
    expect(await auth.google('https://arcana.test/es/diario')).toEqual({ ok: true });
    expect(client.calls.at(-1)).toEqual({ method: 'signInWithOAuth', args: {
      provider: 'google', options: { redirectTo: 'https://arcana.test/es/diario' },
    } });
  });

  it('turns Supabase errors into one readable kind each', async () => {
    const { auth, client } = setup(null);
    client.sendError = { status: 429, code: 'over_email_send_rate_limit' };
    expect(await auth.sendLink('ana@example.com', 'x')).toEqual({ ok: false, error: 'tooOften' });
    expect(sendError({ status: 400, code: 'email_address_invalid' })).toBe('badEmail');
    expect(sendError({ status: 422, code: 'validation_failed', message: 'Unable to validate email address: invalid format' })).toBe('badEmail');
    expect(sendError({ status: 422, code: 'validation_failed', message: 'Password should be at least 6 characters' })).toBe('unavailable');
    expect(sendError({ status: 400, code: 'bad_json' })).toBe('unavailable');
    expect(sendError({ status: 400 })).toBe('unavailable');
    expect(sendError({ status: 422 })).toBe('unavailable');
    expect(sendError({ status: 400, code: 'email_address_not_authorized' })).toBe('unavailable');
    expect(sendError({ status: 500 })).toBe('unavailable');
    expect(sendError({ code: 'over_request_rate_limit' })).toBe('tooOften');
  });

  it('a library that cannot load is "unavailable", never a thrown error', async () => {
    const auth = createAuth(CONFIG, async () => { throw new Error('chunk failed'); }, memoryStorage());
    expect(await auth.session()).toBeNull();
    expect(await auth.sendLink('ana@example.com', 'x')).toEqual({ ok: false, error: 'unavailable' });
  });

  it('signs out this device: the session, the flag and the started mark go', async () => {
    const { auth, client, storage } = setup();
    await auth.token();
    markSignInStarted('email', Date.now(), storage);
    await auth.signOut();
    expect(client.calls.at(-1)).toEqual({ method: 'signOut', args: { scope: 'local' } });
    expect(storage.data[SIGNED_IN_KEY]).toBeUndefined();
    expect(storage.data[STARTED_KEY]).toBeUndefined();
  });

  it('signs out this device even when the library answers an error or throws (review M6)', async () => {
    for (const signOut of [async () => ({ error: { message: 'offline' } }), async () => { throw new Error('offline'); }]) {
      const client = { ...fakeClient(session()), signOut };
      const storage = memoryStorage({ [SIGNED_IN_KEY]: '1' });
      markSignInStarted('email', Date.now(), storage);
      await createAuth(CONFIG, async () => client, storage).signOut();
      expect(storage.data[SIGNED_IN_KEY]).toBeUndefined();
      expect(storage.data[STARTED_KEY]).toBeUndefined();
    }
  });

  it('signs out even when the library cannot load: its stored session and sibling keys go too', async () => {
    const own = [AUTH_STORAGE_KEY, `${AUTH_STORAGE_KEY}-user`, `${AUTH_STORAGE_KEY}-code-verifier`];
    const storage = memoryStorage({ [SIGNED_IN_KEY]: '1', other: 'keep', ...Object.fromEntries(own.map((k) => [k, 'x'])) });
    markSignInStarted('email', Date.now(), storage);
    await createAuth(CONFIG, async () => { throw new Error('chunk failed'); }, storage).signOut();
    expect(storage.data).toEqual({ other: 'keep' });
  });

  it('a transient library error keeps the sign-in; only a clean "no session" clears it', async () => {
    const { auth, client, storage } = setup();
    expect(await auth.token()).toBe('tok-1');
    client.getSession = async () => ({ data: { session: null }, error: { message: 'Failed to fetch' } });
    expect(await auth.session()).toBeNull();
    expect(storage.data[SIGNED_IN_KEY]).toBe('1');
    client.refreshSession = async () => ({ data: { session: null }, error: { message: 'Failed to fetch' } });
    expect(await auth.refresh()).toBeNull();
    expect(storage.data[SIGNED_IN_KEY]).toBe('1');
    client.getSession = async () => ({ data: { session: null }, error: null });
    expect(await auth.session()).toBeNull();
    expect(storage.data[SIGNED_IN_KEY]).toBeUndefined();
  });

  it('a library that failed to load is loaded again on the next use (review M7)', async () => {
    const client = fakeClient(session());
    let tries = 0;
    const auth = createAuth(CONFIG, async () => {
      tries += 1;
      if (tries === 1) throw new Error('chunk failed');
      return client;
    }, memoryStorage());
    expect(await auth.token()).toBeNull(); // offline for a moment
    expect(await auth.token()).toBe('tok-1');
    expect(tries).toBe(2);
  });
});

describe('methodOf', () => {
  it('takes the started mark first, then the provider of the session', () => {
    expect(methodOf(session('t', 'google'), 'email')).toBe('email');
    expect(methodOf(session('t', 'google'), null)).toBe('google');
    expect(methodOf(session('t', 'email'), null)).toBe('email');
    expect(methodOf(null, null)).toBe('email');
  });
});

describe('openSession', () => {
  it('is off, unreachable, signed out or signed in', async () => {
    expect(await openSession(async () => null)).toEqual({ type: 'unreachable' });
    expect(await openSession(async () => ({ ...CONFIG, enabled: false }))).toEqual({ type: 'off' });
    const out = setup(null);
    expect(await openSession(async () => CONFIG, () => out.auth)).toMatchObject({ type: 'signedOut', google: true });
    const signed = setup();
    expect(await openSession(async () => CONFIG, () => signed.auth)).toMatchObject({
      type: 'signedIn', google: true, session: { access_token: 'tok-1' },
    });
  });
});
