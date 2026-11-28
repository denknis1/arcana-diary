import { describe, expect, it } from 'vitest';
import { fakeFetch, jsonResponse } from './testing/fakes';
import { fakeBrowser, MemoryStorage } from './testing/push';
import {
  createPushApi, deniedSeen, DISMISSED_KEY, HOUR_KEY, hourLabel, iosVersion, keyBytes, markDeniedSeen, offerDismissed,
  pushSupport, REFRESHED_KEY, refresh, storedHour, turnOff, turnOn,
} from './push';

const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 Version/18.1 Mobile/15E148 Safari/604.1';
const IPAD = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.1 Safari/605.1.15';
const KEY = 'BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM';

describe('can this browser take a morning reminder (stage 8.1 §2.5)', () => {
  it('yes with a service worker, push and notifications; no without', () => {
    expect(pushSupport(fakeBrowser().env)).toBe('yes');
    expect(pushSupport(fakeBrowser({ push: false }).env)).toBe('no');
  });

  it('an iPhone or iPad outside the Home Screen app gets the hint, inside it the offer', () => {
    expect(pushSupport(fakeBrowser({ userAgent: IPHONE }).env)).toBe('ios-home');
    expect(pushSupport(fakeBrowser({ userAgent: IPAD }).env)).toBe('ios-home'); // iPadOS says Macintosh, with touch
    expect(pushSupport(fakeBrowser({ userAgent: IPHONE, standalone: true }).env)).toBe('yes');
  });

  it('names hours and reads the stored one', () => {
    expect([hourLabel(8, 'en'), hourLabel(20, 'en')]).toEqual(['8:00 AM', '8:00 PM']);
    expect(hourLabel(8, 'es')).toMatch(/^8:00/);
    const storage = new MemoryStorage();
    expect(storedHour(storage)).toBeNull(); // not stored: no hour is invented
    storage.setItem(HOUR_KEY, '6');
    expect(storedHour(storage)).toBe(6);
    storage.setItem(HOUR_KEY, '25');
    expect(storedHour(storage)).toBeNull();
  });

  it('iOS before 16.4 cannot take a reminder even from the Home Screen: no hint, no offer', () => {
    const old = IPHONE.replace('18_1', '16_3');
    expect(iosVersion(old)).toEqual([16, 3]);
    expect(pushSupport(fakeBrowser({ userAgent: old }).env)).toBe('no');
    expect(pushSupport(fakeBrowser({ userAgent: old, standalone: true }).env)).toBe('no');
    expect(pushSupport(fakeBrowser({ userAgent: IPHONE.replace('18_1', '16_4') }).env)).toBe('ios-home');
    expect(pushSupport(fakeBrowser({ userAgent: IPAD.replace('Version/18.1', 'Version/16.2') }).env)).toBe('no');
    expect(pushSupport(fakeBrowser({ userAgent: 'Mozilla/5.0 (iPhone; like Mac OS X) Mobile' }).env)).toBe('ios-home'); // version unknown
  });

  it('the "blocked" line is remembered, and a storage that throws does not break it', () => {
    const storage = new MemoryStorage();
    expect(deniedSeen(storage)).toBe(false);
    markDeniedSeen(storage);
    expect(deniedSeen(storage)).toBe(true);
    const broken = { getItem: () => { throw new Error('no'); }, setItem: () => { throw new Error('no'); }, removeItem: () => {} };
    expect(deniedSeen(broken)).toBe(false);
    expect(() => markDeniedSeen(broken)).not.toThrow();
    expect(storedHour(broken)).toBeNull();
  });

  it('turns the base64url key into the 65 bytes the browser wants', () => {
    const bytes = keyBytes(KEY);
    expect(bytes).toHaveLength(65);
    expect(bytes[0]).toBe(4);
  });

  it('"Not now" hides the offer for 30 days', () => {
    const storage = new MemoryStorage();
    storage.setItem(DISMISSED_KEY, String(Date.UTC(2026, 10, 1)));
    expect(offerDismissed(Date.UTC(2026, 10, 30), storage)).toBe(true);
    expect(offerDismissed(Date.UTC(2026, 11, 2), storage)).toBe(false);
    expect(offerDismissed(Date.UTC(2026, 11, 2), new MemoryStorage())).toBe(false);
  });
});

describe('turning the reminder on and off', () => {
  const deps = (browser: ReturnType<typeof fakeBrowser>, fetched: ReturnType<typeof fakeFetch>, storage = new MemoryStorage()) => ({
    env: browser.env, api: createPushApi(fetched.fetch), storage, lang: 'es' as const, tz: 'America/Mexico_City', today: '2026-11-22',
  });

  it('asks the permission, registers /sw.js, subscribes with the key and tells the API the hour', async () => {
    const browser = fakeBrowser();
    const fetched = fakeFetch(jsonResponse(200, { enabled: true, public_key: KEY }), jsonResponse(201, { hour: 7, tz: 'America/Mexico_City' }));
    const storage = new MemoryStorage();
    expect(await turnOn(deps(browser, fetched, storage), 7)).toBe('on');
    expect([browser.asked, browser.registered]).toEqual([1, ['/sw.js']]);
    expect(browser.subscribed[0].applicationServerKey).toHaveLength(65);
    expect(fetched.calls.map((c) => `${c.method} ${c.url}`)).toEqual(['GET /api/push/key', 'POST /api/push/subscription']);
    expect(fetched.calls[1].body).toEqual({ endpoint: 'https://fcm.googleapis.com/fcm/send/device-1',
      keys: { p256dh: 'BPk', auth: 'au' }, hour: 7, tz: 'America/Mexico_City', lang: 'es' });
    expect([storage.getItem(HOUR_KEY), storage.getItem(REFRESHED_KEY)]).toEqual(['7', '2026-11-22']);
  });

  it('a refused permission registers nothing; reminders off on the server ask nothing', async () => {
    const refused = fakeBrowser({ answer: 'denied' });
    expect(await turnOn(deps(refused, fakeFetch(jsonResponse(200, { enabled: true, public_key: KEY }))), 8)).toBe('denied');
    expect(refused.registered).toEqual([]);
    const off = fakeBrowser();
    const known = { ok: true as const, status: 200, data: { enabled: false, public_key: '' } };
    expect(await turnOn(deps(off, fakeFetch()), 8, known)).toBe('off'); // the key came with the offer: nobody is asked
    expect(off.asked).toBe(0);
    const late = fakeBrowser();
    expect(await turnOn(deps(late, fakeFetch(jsonResponse(200, { enabled: false, public_key: '' }))), 8)).toBe('off');
    expect(late.registered).toEqual([]);
  });

  it('asks the permission first, before any request — the tap is still the tap on an iPhone (review I2)', async () => {
    const fetched = fakeFetch(jsonResponse(200, { enabled: true, public_key: KEY }), jsonResponse(201, { hour: 7, tz: 'UTC' }));
    let requestsWhenAsked = -1;
    const browser = fakeBrowser({ onAsk: () => { requestsWhenAsked = fetched.calls.length; } });
    expect(await turnOn(deps(browser, fetched), 7)).toBe('on');
    expect(requestsWhenAsked).toBe(0);
    // with the key fetched when the offer appeared there is no key request at all after the tap
    const ready = fakeFetch(jsonResponse(201, { hour: 7, tz: 'UTC' }));
    const prefetched = { ok: true as const, status: 200, data: { enabled: true, public_key: KEY } };
    expect(await turnOn(deps(fakeBrowser(), ready), 7, prefetched)).toBe('on');
    expect(ready.calls.map((c) => `${c.method} ${c.url}`)).toEqual(['POST /api/push/subscription']);
  });

  it('an outage or a limit on the key is a failure, not "switched off" (review I5)', async () => {
    for (const status of [503, 429]) {
      const browser = fakeBrowser();
      expect(await turnOn(deps(browser, fakeFetch(jsonResponse(status, { detail: 'x' }))), 8)).toBe('failed');
      expect(browser.registered).toEqual([]);
    }
  });

  it('a closed permission prompt is not an error', async () => {
    const browser = fakeBrowser({ answer: 'default' });
    expect(await turnOn(deps(browser, fakeFetch(jsonResponse(200, { enabled: true, public_key: KEY }))), 8)).toBe('dismissed');
    expect(browser.registered).toEqual([]);
  });

  it('the hour kept here is the one the server answered with', async () => {
    const storage = new MemoryStorage();
    const fetched = fakeFetch(jsonResponse(200, { enabled: true, public_key: KEY }), jsonResponse(201, { hour: 9, tz: 'UTC' }));
    expect(await turnOn(deps(fakeBrowser(), fetched, storage), 7)).toBe('on');
    expect(storage.getItem(HOUR_KEY)).toBe('9');
  });

  it('without a stored hour the daily refresh sends nothing (it would overwrite the server hour)', async () => {
    const browser = fakeBrowser({ permission: 'granted', subscribed: true });
    const fetched = fakeFetch(jsonResponse(201, { hour: 6, tz: 'UTC' }));
    const subscription = (await (await browser.env.serviceWorker!.getRegistration('/'))!.pushManager.getSubscription())!;
    expect(await refresh(deps(browser, fetched), subscription)).toBeNull();
    expect(fetched.calls).toHaveLength(0);
  });

  it('the refresh answer is the hour shown', async () => {
    const browser = fakeBrowser({ permission: 'granted', subscribed: true });
    const fetched = fakeFetch(jsonResponse(201, { hour: 5, tz: 'UTC' }));
    const storage = new MemoryStorage();
    storage.setItem(HOUR_KEY, '6');
    const subscription = (await (await browser.env.serviceWorker!.getRegistration('/'))!.pushManager.getSubscription())!;
    expect(await refresh(deps(browser, fetched, storage), subscription)).toBe(5);
    expect(storage.getItem(HOUR_KEY)).toBe('5');
  });

  it('turning off tells the API and drops the browser subscription', async () => {
    const browser = fakeBrowser({ permission: 'granted', subscribed: true });
    const fetched = fakeFetch(jsonResponse(204, null));
    const storage = new MemoryStorage();
    storage.setItem(HOUR_KEY, '7');
    await turnOff(deps(browser, fetched, storage));
    expect(fetched.calls.map((c) => [c.method, c.url, c.body])).toEqual([
      ['DELETE', '/api/push/subscription', { endpoint: 'https://fcm.googleapis.com/fcm/send/device-1' }]]);
    expect(browser.unsubscribed).toBe(1);
    expect(storage.getItem(HOUR_KEY)).toBeNull();
  });

  it('refreshes once a day with the stored hour', async () => {
    const browser = fakeBrowser({ permission: 'granted', subscribed: true });
    const fetched = fakeFetch(jsonResponse(201, { hour: 6, tz: 'UTC' }));
    const storage = new MemoryStorage();
    storage.setItem(HOUR_KEY, '6');
    const subscription = (await (await browser.env.serviceWorker!.getRegistration('/'))!.pushManager.getSubscription())!;
    await refresh(deps(browser, fetched, storage), subscription);
    await refresh(deps(browser, fetched, storage), subscription);
    expect(fetched.calls).toHaveLength(1);
    expect((fetched.calls[0].body as { hour: number }).hour).toBe(6);
  });
});
