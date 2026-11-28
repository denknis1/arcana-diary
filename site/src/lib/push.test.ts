import { describe, expect, it } from 'vitest';
import { fakeFetch, jsonResponse } from './testing/fakes';
import { fakeBrowser, MemoryStorage } from './testing/push';
import {
  createPushApi, DISMISSED_KEY, HOUR_KEY, hourLabel, keyBytes, offerDismissed, pushSupport, REFRESHED_KEY, refresh,
  storedHour, turnOff, turnOn,
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
    expect(storedHour(storage)).toBe(8);
    storage.setItem(HOUR_KEY, '6');
    expect(storedHour(storage)).toBe(6);
    storage.setItem(HOUR_KEY, '25');
    expect(storedHour(storage)).toBe(8);
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
    expect(await turnOn(deps(off, fakeFetch(jsonResponse(200, { enabled: false, public_key: '' }))), 8)).toBe('off');
    expect(off.asked).toBe(0);
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
