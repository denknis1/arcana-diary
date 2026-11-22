import { describe, expect, it } from 'vitest';
import { createApi } from './api';
import { authFetch, type AuthSource } from './authFetch';
import { SIGNED_IN_KEY } from './authState';
import { memoryStorage } from './testing/auth';
import { fakeFetch, jsonResponse } from './testing/fakes';

function source(tokens: { token: string | null; refresh?: string | null }) {
  const log: string[] = [];
  let loads = 0;
  const auth = {
    token: async () => { log.push('token'); return tokens.token; },
    refresh: async () => { log.push('refresh'); return tokens.refresh ?? null; },
    signOut: async () => { log.push('signOut'); },
  };
  const get: AuthSource = async () => { loads += 1; return auth; };
  return { get, log, loads: () => loads };
}

const SIGNED = () => memoryStorage({ [SIGNED_IN_KEY]: '1' });

describe('authFetch', () => {
  it('a guest request goes as it is and never loads the sign-in library', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, { limit: 2 }));
    const auth = source({ token: 'tok-1' });
    await authFetch(fetch, auth.get, memoryStorage())('/api/limits');
    expect(calls[0].headers.authorization).toBeUndefined();
    expect(auth.loads()).toBe(0);
  });

  it('a signed-in request carries the token and keeps the other headers', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(201, { id: 'r1' }));
    const api = createApi(authFetch(fetch, source({ token: 'tok-1' }).get, SIGNED()));
    await api.createReading({ lang: 'en', kind: 'one' });
    expect(calls[0].headers).toEqual({ 'content-type': 'application/json', authorization: 'Bearer tok-1' });
  });

  it('only /api/* gets the token', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, []));
    await authFetch(fetch, source({ token: 'tok-1' }).get, SIGNED())('/data/daily-en.json');
    expect(calls[0].headers.authorization).toBeUndefined();
  });

  it('401 "auth": one refresh and the same request again with the new token', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(401, { reason: 'auth' }), jsonResponse(200, { items: [] }));
    const auth = source({ token: 'tok-1', refresh: 'tok-2' });
    const response = await authFetch(fetch, auth.get, SIGNED())('/api/diary', { method: 'GET' });
    expect(response.status).toBe(200);
    expect(calls.map((c) => c.headers.authorization)).toEqual(['Bearer tok-1', 'Bearer tok-2']);
    expect(auth.log).toEqual(['token', 'refresh']);
  });

  it('401 "auth" again after the refresh: sign out here and repeat once as a guest', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(401, { reason: 'auth' }), jsonResponse(401, { reason: 'auth' }),
      jsonResponse(201, { id: 'r1' }));
    const auth = source({ token: 'tok-1', refresh: 'tok-2' });
    const body = JSON.stringify({ lang: 'en', kind: 'one' });
    const response = await authFetch(fetch, auth.get, SIGNED())('/api/readings', { method: 'POST', body });
    expect(response.status).toBe(201);
    expect(calls.map((c) => c.headers.authorization)).toEqual(['Bearer tok-1', 'Bearer tok-2', undefined]);
    expect(calls[2].body).toEqual({ lang: 'en', kind: 'one' }); // the same body
    expect(auth.log).toEqual(['token', 'refresh', 'signOut']);
  });

  it('a failed refresh signs out at once', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(401, { reason: 'auth' }), jsonResponse(200, { limit: 2 }));
    const auth = source({ token: 'tok-1', refresh: null });
    await authFetch(fetch, auth.get, SIGNED())('/api/limits');
    expect(calls).toHaveLength(2);
    expect(auth.log).toEqual(['token', 'refresh', 'signOut']);
  });

  it('401 "sign_in", 401 without JSON and 503 come back unchanged, with no refresh', async () => {
    for (const answer of [jsonResponse(401, { reason: 'sign_in' }), new Response('Unauthorized', { status: 401 }),
      jsonResponse(503, { reason: 'auth_unavailable' })]) {
      const { fetch, calls } = fakeFetch(answer);
      const auth = source({ token: 'tok-1', refresh: 'tok-2' });
      const response = await authFetch(fetch, auth.get, SIGNED())('/api/account');
      expect(response).toBe(answer);
      expect(calls).toHaveLength(1);
      expect(auth.log).toEqual(['token']);
    }
  });

  it('the caller still reads the body of a refusal it gets back', async () => {
    const { fetch } = fakeFetch(jsonResponse(401, { reason: 'sign_in' }));
    const api = createApi(authFetch(fetch, source({ token: 'tok-1' }).get, SIGNED()));
    expect(await api.getReading('r1', undefined)).toMatchObject({ ok: false, status: 401, body: { reason: 'sign_in' } });
  });

  it('a flag without a session (signed out in another tab) is a guest request', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, { limit: 2 }));
    await authFetch(fetch, source({ token: null }).get, SIGNED())('/api/limits');
    expect(calls[0].headers.authorization).toBeUndefined();
  });

  it('sign-in off (no Auth) is a guest request', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, { limit: 2 }));
    await authFetch(fetch, async () => null, SIGNED())('/api/limits');
    expect(calls[0].headers.authorization).toBeUndefined();
  });
});
