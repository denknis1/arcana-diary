import { describe, expect, it, vi } from 'vitest';
import { swSource, swTexts } from './sw';

type Listener = (event: Record<string, unknown>) => void;

/** Runs the service worker's text against a stand-in for its global scope. */
function worker(windows: Array<{ url: string; focus: () => Promise<unknown> }> = []) {
  const listeners: Record<string, Listener> = {};
  const shown: Array<[string, Record<string, unknown>]> = [];
  const waits: Array<Promise<unknown>> = [];
  const scope = {
    addEventListener: (name: string, listener: Listener) => { listeners[name] = listener; },
    skipWaiting: vi.fn(),
    registration: { showNotification: async (title: string, options: Record<string, unknown>) => { shown.push([title, options]); } },
    clients: { claim: vi.fn(async () => {}), matchAll: vi.fn(async () => windows), openWindow: vi.fn(async () => null) },
  };
  const fetchFn = vi.fn(async () => new Response(null, { status: 204 }));
  new Function('self', 'fetch', swSource(swTexts()))(scope, fetchFn);
  const fire = async (name: string, event: Record<string, unknown>) => {
    listeners[name]({ ...event, waitUntil: (p: Promise<unknown>) => waits.push(p) });
    await Promise.all(waits);
  };
  return { listeners, shown, scope, fetchFn, fire };
}

describe('the service worker (stage 8.1 §4)', () => {
  it('shows the morning reminder in the language of the message, never a card', async () => {
    const sw = worker();
    await sw.fire('push', { data: { json: () => ({ lang: 'es', card: 'La Luna' }) } });
    expect(sw.shown).toEqual([['Arcana Diary', { body: 'Tu carta de hoy te espera', icon: '/icon-192.png', tag: 'daily',
      data: { lang: 'es' } }]]);
    await sw.fire('push', { data: { json: () => { throw new Error('not JSON'); } } });
    expect(sw.shown[1][1].body).toBe('Your card for today is waiting');
  });

  it('a click opens the Card of the Day of its language and is counted', async () => {
    const sw = worker();
    const close = vi.fn();
    await sw.fire('notificationclick', { notification: { close, data: { lang: 'es' } } });
    expect(close).toHaveBeenCalled();
    expect(sw.scope.clients.openWindow).toHaveBeenCalledWith('/es/carta-del-dia');
    const [url, init] = sw.fetchFn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/events');
    expect(JSON.parse(String(init.body))).toEqual({ name: 'push_click', tool: null, lang: 'es', params: {} });
  });

  it('a click focuses an open Card of the Day instead of opening another', async () => {
    const focus = vi.fn(async () => null);
    const sw = worker([{ url: 'https://arcanadiary.com/daily', focus }]);
    await sw.fire('notificationclick', { notification: { close: vi.fn(), data: { lang: 'en' } } });
    expect(focus).toHaveBeenCalled();
    expect(sw.scope.clients.openWindow).not.toHaveBeenCalled();
  });

  it('caches nothing: there is no fetch handler', () => {
    expect(Object.keys(worker().listeners).sort()).toEqual(['activate', 'install', 'notificationclick', 'push']);
  });
});
