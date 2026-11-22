import { describe, expect, it } from 'vitest';
import type { AnalyticsEvent } from './analytics';
import { STARTED_KEY, markSignInStarted } from './authState';
import { cleanReturnUrl, finishSignIn, linkFailed, readReturnParams, returnUrl, type FinishDeps } from './claim';
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
    storage, href, lang: 'en', now: 1000,
    method: (started) => started ?? 'email',
    replaceUrl: (url) => urls.push(url),
    send: (event) => events.push(event),
    ...overrides,
  };
  return { d, calls, events, urls, storage };
}

describe('finishSignIn', () => {
  it('with only a token in the address (the link opened on another device): claims that reading only, gives consent, counts signup_done and cleans the address', async () => {
    const { d, calls, events, urls } = deps('https://arcana.test/diary?claim=tok&remind=1');
    expect(await finishSignIn(d)).toEqual({ type: 'claimed', claimed: ['r1'] });
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
    expect(await finishSignIn(d)).toMatchObject({ type: 'claimed' });
    expect(calls).toEqual(['claim [] device']);
    expect(events[0].params).toEqual({ method: 'google' });
    expect(storage.data[STARTED_KEY]).toBeUndefined(); // once: the next visit claims nothing
    expect(await finishSignIn(d)).toEqual({ type: 'none' });
    expect(calls).toHaveLength(1);
  });

  it('a token that moves nothing, without the mark (made up, or the same link again after Back): no consent, no signup_done, a clean address (review I1)', async () => {
    const { d, calls, events, urls } = deps('https://arcana.test/diary?claim=used&remind=1', {
      api: {
        claim: async (tokens, device) => {
          calls.push(`claim ${JSON.stringify(tokens)} ${device ? 'device' : 'tokens only'}`);
          return { ok: true, status: 200, data: { claimed: [] } };
        },
        setConsent: async () => { throw new Error('must not be called'); },
      },
    });
    expect(await finishSignIn(d)).toEqual({ type: 'claimed', claimed: [] });
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
    const { d, calls } = deps('https://arcana.test/diary?claim=tok');
    await Promise.all([finishSignIn(d), finishSignIn(d)]);
    expect(calls).toEqual(['claim ["tok"] tokens only']);
  });
});

describe('linkFailed', () => {
  it('sees the error Supabase puts in the address of an expired link', () => {
    expect(linkFailed('#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid')).toBe(true);
    expect(linkFailed('#access_token=x&type=magiclink')).toBe(false);
    expect(linkFailed('')).toBe(false);
  });
});
