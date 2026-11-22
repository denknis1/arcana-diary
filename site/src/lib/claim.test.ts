import { describe, expect, it } from 'vitest';
import type { AnalyticsEvent } from './analytics';
import { STARTED_KEY, markSignInStarted } from './authState';
import {
  cleanReturnUrl, finishSignIn, hashAccessToken, linkFailed, readReturnParams, returnUrl, type FinishDeps,
} from './claim';
import { memoryStorage } from './testing/auth';

describe('the return address', () => {
  it('is the diary of the page language, with the claim token and the reminder', () => {
    expect(returnUrl('https://arcana.test', 'en')).toBe('https://arcana.test/diary');
    expect(returnUrl('https://arcana.test', 'es', { claim: 'a-b_c', remind: true })).toBe('https://arcana.test/es/diario?claim=a-b_c&remind=1');
    expect(returnUrl('https://arcana.test', 'en', { claim: null, remind: true })).toBe('https://arcana.test/diary?remind=1');
  });

  it('is read back, and cleaned of claim and remind only', () => {
    expect(readReturnParams('?claim=tok&remind=1&r=x')).toEqual({ claim: 'tok', remind: true });
    expect(readReturnParams('?claim=' + 'x'.repeat(101))).toEqual({ claim: null, remind: false });
    expect(cleanReturnUrl('https://arcana.test/diary?claim=tok&remind=1&r=abc')).toBe('/diary?r=abc');
    expect(cleanReturnUrl('https://arcana.test/es/diario?claim=tok')).toBe('/es/diario');
    expect(cleanReturnUrl('https://arcana.test/diary?claim=tok#access_token=secret&type=magiclink')).toBe('/diary');
  });
});

function deps(href: string, overrides: Partial<FinishDeps> = {}) {
  const calls: string[] = [];
  const events: AnalyticsEvent[] = [];
  const urls: string[] = [];
  const storage = memoryStorage();
  const d: FinishDeps = {
    api: {
      claim: async (tokens, device) => {
        calls.push(`claim ${JSON.stringify(tokens)} ${device ? 'device' : 'tokens only'}`);
        return { ok: true, status: 200, data: { claimed: tokens.length || device ? ['r1'] : [] } };
      },
      setConsent: async (on) => { calls.push(`consent ${on}`); return { ok: true, status: 200, data: { email: null, reminders_consent: on, consent_at: null } }; },
    },
    storage, href, lang: 'en', now: 1000, arrivedWithSession: false,
    method: (started) => started ?? 'email',
    replaceUrl: (url) => urls.push(url),
    send: (event) => events.push(event),
    ...overrides,
  };
  return { d, calls, events, urls, storage };
}

describe('finishSignIn', () => {
  it('right after a sign-in by the link opened on another device (the session came in the address, no mark): claims that reading only, gives consent, counts signup_done and cleans the address', async () => {
    const { d, calls, events, urls } = deps('https://arcana.test/diary?claim=tok&remind=1', { arrivedWithSession: true });
    expect(await finishSignIn(d)).toEqual({ type: 'claimed', claimed: ['r1'], consent: 'set' });
    expect(calls).toEqual(['claim ["tok"] tokens only', 'consent true']); // owner decision 12: not this browser's readings
    expect(events).toEqual([{ name: 'signup_done', tool: null, lang: 'en', params: { method: 'email' } }]);
    expect(urls).toEqual(['/diary']);
  });

  it('with the token and the mark (the link opened on the device that sent it): the token and this device', async () => {
    const { d, calls, storage } = deps('https://arcana.test/diary?claim=tok&remind=1');
    markSignInStarted('email', 900, storage);
    await finishSignIn(d);
    expect(calls).toEqual(['claim ["tok"] device', 'consent true']);
  });

  it('after a sign-in started here: claims this device with no token, with its method', async () => {
    const { d, calls, events, storage } = deps('https://arcana.test/diary');
    markSignInStarted('google', 900, storage);
    expect(await finishSignIn(d)).toEqual({ type: 'claimed', claimed: ['r1'], consent: 'none' });
    expect(calls).toEqual(['claim [] device']);
    expect(events[0].params).toEqual({ method: 'google' });
    expect(storage.data[STARTED_KEY]).toBeUndefined(); // once: the next visit claims nothing
    expect(await finishSignIn(d)).toEqual({ type: 'none' });
    expect(calls).toHaveLength(1);
  });

  it('a token that moves nothing, without the mark (made up, or the same link again after Back): no consent, no signup_done, a clean address (review I1)', async () => {
    const { d, calls, events, urls } = deps('https://arcana.test/diary?claim=used&remind=1', {
      arrivedWithSession: true,
      api: {
        claim: async (tokens, device) => {
          calls.push(`claim ${JSON.stringify(tokens)} ${device ? 'device' : 'tokens only'}`);
          return { ok: true, status: 200, data: { claimed: [] } };
        },
        setConsent: async () => { throw new Error('must not be called'); },
      },
    });
    expect(await finishSignIn(d)).toEqual({ type: 'claimed', claimed: [], consent: 'none' });
    expect(calls).toEqual(['claim ["used"] tokens only']);
    expect(events).toEqual([]);
    expect(urls).toEqual(['/diary']);
  });

  it('an ordinary visit claims nothing (a shared computer keeps its guest readings)', async () => {
    const { d, calls, events, urls } = deps('https://arcana.test/diary?r=abc');
    expect(await finishSignIn(d)).toEqual({ type: 'none' });
    expect(calls).toEqual([]);
    expect(events).toEqual([]);
    expect(urls).toEqual([]);
  });

  it('a failed claim changes nothing, so a reload tries again', async () => {
    const { d, calls, urls, storage } = deps('https://arcana.test/diary?claim=tok', {
      api: { claim: async () => ({ ok: false, status: 503, error: 'unavailable', body: null }), setConsent: async () => { throw new Error('no'); } },
    });
    markSignInStarted('email', 900, storage);
    expect(await finishSignIn(d)).toEqual({ type: 'error', error: 'unavailable' });
    expect(urls).toEqual([]);
    expect(storage.data[STARTED_KEY]).toBeDefined();
    expect(calls).toEqual([]);
  });

  it('runs once when two parts of the page ask at the same time', async () => {
    const { d, calls } = deps('https://arcana.test/diary?claim=tok', { arrivedWithSession: true });
    await Promise.all([finishSignIn(d), finishSignIn(d)]);
    expect(calls).toEqual(['claim ["tok"] tokens only']);
  });
});

describe('finishSignIn counts a claim link only right after a sign-in (owner decision 15)', () => {
  it('someone else\'s link opened by a person already signed in (no mark, no session in the address): nothing is claimed, no consent, no event; only the address is cleaned', async () => {
    const { d, calls, events, urls } = deps('https://arcana.test/diary?claim=valid-of-someone-else&remind=1&r=abc');
    expect(await finishSignIn(d)).toEqual({ type: 'none' });
    expect(calls).toEqual([]);
    expect(events).toEqual([]);
    expect(urls).toEqual(['/diary?r=abc']);
  });

  it('/diary?remind=1 without the mark or a session in the address: no calls, the address becomes /diary', async () => {
    const { d, calls, events, urls } = deps('https://arcana.test/diary?remind=1');
    expect(await finishSignIn(d)).toEqual({ type: 'none' });
    expect(calls).toEqual([]);
    expect(events).toEqual([]);
    expect(urls).toEqual(['/diary']);
  });

  it('the session in the address with a token and no reminder: claims the token only, no consent, signup_done', async () => {
    const { d, calls, events, urls } = deps('https://arcana.test/es/diario?claim=tok', { arrivedWithSession: true, lang: 'es' });
    expect(await finishSignIn(d)).toEqual({ type: 'claimed', claimed: ['r1'], consent: 'none' });
    expect(calls).toEqual(['claim ["tok"] tokens only']);
    expect(events).toEqual([{ name: 'signup_done', tool: null, lang: 'es', params: { method: 'email' } }]);
    expect(urls).toEqual(['/es/diario']);
  });

  it('the session in the address with no token and no mark (a returning person who signed in from an old e-mail): nothing to claim', async () => {
    const { d, calls, events, urls } = deps('https://arcana.test/diary', { arrivedWithSession: true });
    expect(await finishSignIn(d)).toEqual({ type: 'none' });
    expect(calls).toEqual([]);
    expect(events).toEqual([]);
    expect(urls).toEqual([]);
  });

  it('a failed consent PATCH is reported, not swallowed (review Minor 2)', async () => {
    const { d, calls, events, urls } = deps('https://arcana.test/diary?claim=tok&remind=1', {
      arrivedWithSession: true,
      api: {
        claim: async () => { calls.push('claim'); return { ok: true, status: 200, data: { claimed: ['r1'] } }; },
        setConsent: async () => { calls.push('consent'); return { ok: false, status: 503, error: 'unavailable', body: null }; },
      },
    });
    expect(await finishSignIn(d)).toEqual({ type: 'claimed', claimed: ['r1'], consent: 'failed' });
    expect(calls).toEqual(['claim', 'consent']);
    expect(events.map((e) => e.name)).toEqual(['signup_done']); // the sign-up itself did happen
    expect(urls).toEqual(['/diary']);
  });
});

describe('hashAccessToken', () => {
  it('reads the access token of the implicit flow from the address hash (the e-mail link and Google alike)', () => {
    expect(hashAccessToken('#access_token=x&expires_in=3600&refresh_token=y&token_type=bearer&type=magiclink')).toBe('x');
    expect(hashAccessToken('#access_token=eyJ.a-b_c&expires_at=1&provider_token=g&refresh_token=y&token_type=bearer'))
      .toBe('eyJ.a-b_c');
    expect(hashAccessToken('access_token=x')).toBe('x');
  });

  it('is null for a failed link, an empty token, another anchor or no hash', () => {
    expect(hashAccessToken('#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid')).toBeNull();
    expect(hashAccessToken('#access_token=')).toBeNull();
    expect(hashAccessToken('#top')).toBeNull();
    expect(hashAccessToken('#')).toBeNull();
    expect(hashAccessToken('')).toBeNull();
  });
});

describe('linkFailed', () => {
  it('sees the error Supabase puts in the address of an expired link', () => {
    expect(linkFailed('#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid')).toBe(true);
    expect(linkFailed('#access_token=x&type=magiclink')).toBe(false);
    expect(linkFailed('')).toBe(false);
  });
});
