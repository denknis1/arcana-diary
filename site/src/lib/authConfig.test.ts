import { afterEach, describe, expect, it } from 'vitest';
import { AUTH_CONFIG_URL, authConfig, fetchAuthConfig, forgetAuthConfig, parseAuthConfig } from './authConfig';
import { fakeFetch, jsonResponse } from './testing/fakes';

const ON = { enabled: true, supabase_url: 'https://abc.supabase.co', anon_key: 'sb_publishable_x', google: true };

afterEach(() => forgetAuthConfig());

describe('auth config', () => {
  it('reads the settings of GET /api/auth-config', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, ON));
    expect(await fetchAuthConfig(fetch)).toEqual(ON);
    expect(calls[0]).toMatchObject({ url: AUTH_CONFIG_URL, method: 'GET' });
  });

  it('is off without an https address or a key, whatever "enabled" says', () => {
    expect(parseAuthConfig({ ...ON, supabase_url: 'http://abc.supabase.co' }).enabled).toBe(false);
    expect(parseAuthConfig({ ...ON, anon_key: '' })).toEqual({ enabled: false, supabase_url: '', anon_key: '', google: false });
    expect(parseAuthConfig({ enabled: false, supabase_url: '', anon_key: '', google: false }).enabled).toBe(false);
    expect(parseAuthConfig('nonsense').enabled).toBe(false);
    expect(parseAuthConfig({ ...ON, google: 'yes' }).google).toBe(false);
  });

  it('is null when it cannot be read, and asks again next time', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(503, { reason: 'db' }), new TypeError('offline'), jsonResponse(200, ON));
    expect(await authConfig(fetch)).toBeNull();
    expect(await authConfig(fetch)).toBeNull();
    expect(await authConfig(fetch)).toEqual(ON);
    expect(await authConfig(fetch)).toEqual(ON); // cached: no fourth request
    expect(calls).toHaveLength(3);
  });
});
