// A browser with (or without) Web Push, for the reminder tests: a fake service worker container, push manager and
// Notification permission. Nothing here talks to a real push service.
import type { PushEnv } from '../push';

export interface FakeBrowser {
  env: PushEnv;
  registered: string[];
  subscribed: Array<{ applicationServerKey: Uint8Array }>;
  unsubscribed: number;
  asked: number;
}

export function fakeBrowser(options: { permission?: NotificationPermission; answer?: NotificationPermission;
  subscribed?: boolean; userAgent?: string; standalone?: boolean; push?: boolean } = {}): FakeBrowser {
  const state: FakeBrowser = { env: undefined as unknown as PushEnv, registered: [], subscribed: [], unsubscribed: 0, asked: 0 };
  let subscription: PushSubscription | null = null;
  const make = () => ({
    endpoint: 'https://fcm.googleapis.com/fcm/send/device-1',
    toJSON: () => ({ endpoint: 'https://fcm.googleapis.com/fcm/send/device-1', keys: { p256dh: 'BPk', auth: 'au' } }),
    unsubscribe: async () => { state.unsubscribed += 1; subscription = null; return true; },
  }) as unknown as PushSubscription;
  if (options.subscribed) subscription = make();
  const pushManager = {
    getSubscription: async () => subscription,
    subscribe: async (init: { applicationServerKey: Uint8Array }) => { state.subscribed.push(init); subscription = make(); return subscription; },
  };
  const registration = { pushManager } as unknown as ServiceWorkerRegistration;
  let registeredYet = Boolean(options.subscribed);
  const notification = {
    permission: options.permission ?? 'default',
    requestPermission: async () => { state.asked += 1; notification.permission = options.answer ?? 'granted'; return notification.permission; },
  };
  state.env = {
    serviceWorker: {
      register: async (url: string) => { state.registered.push(url); registeredYet = true; return registration; },
      getRegistration: async () => (registeredYet ? registration : undefined),
    } as unknown as ServiceWorkerContainer,
    pushManager: options.push ?? true,
    notification,
    userAgent: options.userAgent ?? 'Mozilla/5.0 (Linux; Android 14) Chrome/131',
    maxTouchPoints: 5,
    standalone: options.standalone ?? false,
  };
  return state;
}

export class MemoryStorage {
  items = new Map<string, string>();
  getItem(key: string) { return this.items.get(key) ?? null; }
  setItem(key: string, value: string) { this.items.set(key, value); }
  removeItem(key: string) { this.items.delete(key); }
}
