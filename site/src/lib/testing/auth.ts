// Test doubles for signing in: an in-memory storage and a fake sign-in library client (no network, no
// @supabase/auth-js).
import type { AuthClientLike, AuthErrorLike, SessionLike } from '../auth';
import type { StorageLike } from '../authState';

export function memoryStorage(initial: Record<string, string> = {}): StorageLike & { data: Record<string, string> } {
  const data = { ...initial };
  return {
    data,
    getItem: (key) => (key in data ? data[key] : null),
    setItem: (key, value) => { data[key] = value; },
    removeItem: (key) => { delete data[key]; },
  };
}

export interface FakeClient extends AuthClientLike {
  calls: Array<{ method: string; args: unknown }>;
  session: SessionLike | null;
  refreshed: SessionLike | null;
  sendError: AuthErrorLike | null;
}

export function fakeClient(session: SessionLike | null = null): FakeClient {
  const client: FakeClient = {
    calls: [],
    session,
    refreshed: null,
    sendError: null,
    async getSession() {
      client.calls.push({ method: 'getSession', args: null });
      return { data: { session: client.session }, error: null };
    },
    async refreshSession() {
      client.calls.push({ method: 'refreshSession', args: null });
      client.session = client.refreshed;
      return { data: { session: client.refreshed }, error: client.refreshed ? null : { message: 'refresh failed' } };
    },
    async signInWithOtp(args) {
      client.calls.push({ method: 'signInWithOtp', args });
      return { error: client.sendError };
    },
    async signInWithOAuth(args) {
      client.calls.push({ method: 'signInWithOAuth', args });
      return { error: client.sendError };
    },
    async signOut(args) {
      client.calls.push({ method: 'signOut', args });
      client.session = null;
      return { error: null };
    },
  };
  return client;
}

export function session(token = 'tok-1', provider = 'email', email = 'ana@example.com'): SessionLike {
  return { access_token: token, user: { email, app_metadata: { provider } } };
}
