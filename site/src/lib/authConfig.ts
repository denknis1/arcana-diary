// The public sign-in settings (spec 4.4b §3): GET /api/auth-config → {"enabled", "supabase_url", "anon_key",
// "google"}. Read once per page; nothing here loads the sign-in library.
import type { FetchFn } from './api';

export interface AuthConfig {
  enabled: boolean;
  supabase_url: string;
  anon_key: string;
  google: boolean;
}

export const AUTH_CONFIG_URL = '/api/auth-config';

/** The answer as the site may trust it: on only with an https address and a key. */
export function parseAuthConfig(body: unknown): AuthConfig {
  const b = (body && typeof body === 'object' ? body : {}) as Record<string, unknown>;
  const url = typeof b.supabase_url === 'string' ? b.supabase_url : '';
  const key = typeof b.anon_key === 'string' ? b.anon_key : '';
  const enabled = b.enabled === true && url.startsWith('https://') && key !== '';
  return { enabled, supabase_url: enabled ? url : '', anon_key: enabled ? key : '', google: enabled && b.google === true };
}

/** null when the settings could not be read (offline, the API down): the caller says "try later". */
export async function fetchAuthConfig(fetchFn: FetchFn): Promise<AuthConfig | null> {
  try {
    const response = await fetchFn(AUTH_CONFIG_URL, { method: 'GET' });
    if (!response.ok) return null;
    return parseAuthConfig(await response.json());
  } catch {
    return null;
  }
}

let cached: Promise<AuthConfig | null> | null = null;

/** One request per page; a failed one is asked again next time. */
export function authConfig(fetchFn: FetchFn = (input, init) => fetch(input, init)): Promise<AuthConfig | null> {
  if (!cached) {
    cached = fetchAuthConfig(fetchFn).then((config) => {
      if (config === null) cached = null;
      return config;
    });
  }
  return cached;
}

export function forgetAuthConfig(): void {
  cached = null;
}
