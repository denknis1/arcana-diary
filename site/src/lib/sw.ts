// The service worker /sw.js (stage 8.1 §4), written at build time by src/pages/sw.js.ts so that its two lines come
// from the dictionaries. It only shows the morning reminder and opens the Card of the Day: no fetch handler, nothing
// of the site is cached. The message from the server carries only the language; the address it opens is fixed here,
// so a message can never send the browser anywhere else. A click is counted as push_click (no tool, no params).
import { DICTS } from '../i18n';
import { pagePath } from './routes';
import { LANGS, type Lang } from './types';

export type SwTexts = Record<Lang, { title: string; body: string; url: string }>;

export function swTexts(): SwTexts {
  const entry = (lang: Lang) => ({ title: DICTS[lang].notifTitle, body: DICTS[lang].notifBody, url: pagePath('daily', lang) });
  return Object.fromEntries(LANGS.map((lang) => [lang, entry(lang)])) as SwTexts;
}

export function swSource(texts: SwTexts): string {
  return `// Arcana Diary service worker (stage 8.1): shows the morning reminder and opens the Card of the Day.
// No fetch handler: the site is never cached here.
const TEXTS = ${JSON.stringify(texts)};
const langOf = (value) => (value === 'es' ? 'es' : 'en');
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));
self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (error) { data = {}; }
  const lang = langOf(data && data.lang);
  event.waitUntil(self.registration.showNotification(TEXTS[lang].title, {
    body: TEXTS[lang].body, icon: '/icon-192.png', tag: 'daily', data: { lang },
  }));
});
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const lang = langOf(event.notification.data && event.notification.data.lang);
  const url = TEXTS[lang].url;
  const counted = fetch('/api/events', {
    method: 'POST', headers: { 'content-type': 'application/json' }, keepalive: true, credentials: 'same-origin',
    body: JSON.stringify({ name: 'push_click', tool: null, lang, params: {} }),
  }).catch(() => {});
  const opened = self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
    for (const client of list) {
      if (new URL(client.url).pathname === url && 'focus' in client) return client.focus();
    }
    return self.clients.openWindow(url);
  });
  event.waitUntil(Promise.all([counted, opened]));
});
`;
}
