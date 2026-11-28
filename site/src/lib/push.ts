// The morning reminder in the browser (stage 8.1 §2.5): can this browser take it, turn it on (permission, the
// service worker, the subscription, POST /api/push/subscription), turn it off, and refresh it once a day so the server
// knows the time zone and that the browser still wants it. The service worker is registered only when the person
// turns the reminder on. Local storage keeps only the chosen hour and two dates (the privacy page says so).
import { callJson, type ApiResult, type FetchFn } from './api';
import type { StorageLike } from './authState';
import type { Lang } from './types';

export const SW_URL = '/sw.js';
export const HOUR_KEY = 'ad_push_hour';
export const REFRESHED_KEY = 'ad_push_refreshed';
export const DISMISSED_KEY = 'ad_push_dismissed';
export const DEFAULT_HOUR = 8;
export const OFFER_STREAK = 3; // spec §2.5: the offer comes after the third day in a row
export const DISMISS_DAYS = 30;

export interface PushEnv {
  serviceWorker?: ServiceWorkerContainer;
  pushManager: boolean;
  notification?: { permission: NotificationPermission; requestPermission(): Promise<NotificationPermission> };
  userAgent: string;
  maxTouchPoints: number;
  standalone: boolean;
}

export function browserEnv(): PushEnv {
  const nav = typeof navigator === 'undefined' ? undefined : navigator;
  const standalone = typeof matchMedia === 'function' && matchMedia('(display-mode: standalone)').matches;
  return {
    serviceWorker: nav && 'serviceWorker' in nav ? nav.serviceWorker : undefined,
    pushManager: typeof window !== 'undefined' && 'PushManager' in window,
    notification: typeof Notification === 'undefined' ? undefined : Notification,
    userAgent: nav?.userAgent ?? '',
    maxTouchPoints: nav?.maxTouchPoints ?? 0,
    standalone: standalone || (nav as { standalone?: boolean } | undefined)?.standalone === true,
  };
}

/** 'yes' — the offer; 'ios-home' — an iPhone or iPad outside the Home Screen app: the hint how to add it there
 * (Safari gives reminders only to sites opened from the Home Screen); 'no' — nothing. */
export type Support = 'yes' | 'ios-home' | 'no';

export function pushSupport(env: PushEnv): Support {
  const ios = /iPhone|iPad|iPod/.test(env.userAgent) || (/Macintosh/.test(env.userAgent) && env.maxTouchPoints > 1);
  if (ios && !env.standalone) return 'ios-home';
  return env.serviceWorker && env.pushManager && env.notification ? 'yes' : 'no';
}

/** "8:00 AM" / "8:00 a.m." — an hour of the day as people read it. */
export function hourLabel(hour: number, lang: Lang): string {
  return new Intl.DateTimeFormat(lang === 'en' ? 'en-US' : 'es-MX', { hour: 'numeric', minute: '2-digit', timeZone: 'UTC' })
    .format(new Date(Date.UTC(2026, 0, 1, hour)));
}

export function keyBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (base64url.length % 4)) % 4);
  const text = atob(base64);
  const bytes = new Uint8Array(new ArrayBuffer(text.length));
  for (let i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i);
  return bytes;
}

export function storedHour(storage: StorageLike | null): number {
  const text = storage?.getItem(HOUR_KEY) ?? null;
  const hour = text === null || text === '' ? NaN : Number(text);
  return Number.isInteger(hour) && hour >= 0 && hour <= 23 ? hour : DEFAULT_HOUR;
}

export function offerDismissed(now: number, storage: StorageLike | null): boolean {
  const at = Number(storage?.getItem(DISMISSED_KEY));
  return Number.isFinite(at) && at > 0 && now - at < DISMISS_DAYS * 86_400_000;
}

export interface SubscriptionBody {
  endpoint: string;
  keys: { p256dh: string; auth: string };
  hour: number;
  tz?: string;
  lang: Lang;
}

export interface PushApi {
  key(): Promise<ApiResult<{ enabled: boolean; public_key: string }>>;
  subscribe(body: SubscriptionBody): Promise<ApiResult<{ hour: number; tz: string }>>;
  unsubscribe(endpoint: string): Promise<ApiResult<null>>;
}

export function createPushApi(fetchFn: FetchFn): PushApi {
  const json = (method: string, body: unknown): RequestInit => ({
    method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
  });
  return {
    key: () => callJson(fetchFn, '/api/push/key'),
    subscribe: (body) => callJson(fetchFn, '/api/push/subscription', json('POST', body)),
    unsubscribe: (endpoint) => callJson(fetchFn, '/api/push/subscription', json('DELETE', { endpoint })),
  };
}

function bodyOf(subscription: PushSubscription, hour: number, tz: string | undefined, lang: Lang): SubscriptionBody {
  const keys = subscription.toJSON().keys ?? {};
  return { endpoint: subscription.endpoint, keys: { p256dh: keys.p256dh ?? '', auth: keys.auth ?? '' }, hour, tz, lang };
}

/** The browser's subscription, without registering anything. */
export async function currentSubscription(env: PushEnv): Promise<PushSubscription | null> {
  try {
    const registration = await env.serviceWorker?.getRegistration('/');
    return (await registration?.pushManager.getSubscription()) ?? null;
  } catch {
    return null;
  }
}

export type TurnOn = 'on' | 'denied' | 'off' | 'failed';

export interface PushDeps {
  env: PushEnv;
  api: PushApi;
  storage: StorageLike | null;
  lang: Lang;
  tz: string | undefined;
  today: string;
}

export async function turnOn(deps: PushDeps, hour: number): Promise<TurnOn> {
  const { env, api, storage, lang, tz, today } = deps;
  if (!env.serviceWorker || !env.notification) return 'off';
  const key = await api.key();
  if (!key.ok || !key.data.enabled || !key.data.public_key) return 'off';
  try {
    const permission = await env.notification.requestPermission();
    if (permission === 'denied') return 'denied';
    if (permission !== 'granted') return 'failed';
    const registration = await env.serviceWorker.register(SW_URL, { scope: '/' });
    const subscription = (await registration.pushManager.getSubscription())
      ?? (await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(key.data.public_key) }));
    const saved = await api.subscribe(bodyOf(subscription, hour, tz, lang));
    if (!saved.ok) return 'failed';
    storage?.setItem(HOUR_KEY, String(hour));
    storage?.setItem(REFRESHED_KEY, today);
    return 'on';
  } catch {
    return 'failed';
  }
}

export async function turnOff(deps: Pick<PushDeps, 'env' | 'api' | 'storage'>): Promise<boolean> {
  const subscription = await currentSubscription(deps.env);
  if (subscription) {
    await deps.api.unsubscribe(subscription.endpoint);
    try {
      await subscription.unsubscribe();
    } catch {
      // the server row is gone already: nothing more is sent
    }
  }
  deps.storage?.removeItem(HOUR_KEY);
  deps.storage?.removeItem(REFRESHED_KEY);
  return true;
}

/** Once a day while the reminder is on: the same subscription again, with today's time zone. */
export async function refresh(deps: PushDeps, subscription: PushSubscription): Promise<void> {
  if (deps.storage?.getItem(REFRESHED_KEY) === deps.today) return;
  const saved = await deps.api.subscribe(bodyOf(subscription, storedHour(deps.storage), deps.tz, deps.lang));
  if (saved.ok) deps.storage?.setItem(REFRESHED_KEY, deps.today);
}
