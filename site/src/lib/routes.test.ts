import { describe, expect, it } from 'vitest';
import pairs from '../data/pairs.json';
import { DECK } from './deck';
import { NAV_KEYS, PRIVATE_PAIRS, allPagePaths, cardPath, distFile, langOf, pagePath, switchPath } from './routes';

describe('routes', () => {
  it('lists every page of spec §3 for both languages', () => {
    const paths = allPagePaths();
    expect(paths).toHaveLength(8 + 78 + 7 + 78);
    for (const p of ['/', '/one-card', '/yes-no', '/love', '/daily', '/diary', '/account', '/404', '/es', '/es/si-o-no',
      '/es/amor', '/es/carta-del-dia', '/es/diario', '/es/cuenta', '/es/404', '/cards/the-moon', '/es/cartas/la-luna']) {
      expect(paths).toContain(p);
    }
    expect(new Set(paths).size).toBe(paths.length);
  });

  it('puts the Spanish one-card mode on the home page section #una-carta', () => {
    expect(pagePath('one_card', 'es')).toBe('/es#una-carta');
    expect(pagePath('one_card', 'en')).toBe('/one-card');
  });

  it('switches language by the pairs of hreflang.csv', () => {
    expect(switchPath('/')).toBe('/es');
    expect(switchPath('/es')).toBe('/');
    expect(switchPath('/one-card')).toBe('/es');
    expect(switchPath('/es/si-o-no')).toBe('/yes-no');
    expect(switchPath('/daily')).toBe('/es/carta-del-dia');
    expect(switchPath('/cards/the-moon')).toBe('/es/cartas/la-luna');
    expect(switchPath('/es/cartas/el-loco')).toBe('/cards/the-fool');
    expect(switchPath('/404')).toBe('/es/404');
    expect(switchPath('/es/404')).toBe('/404');
    expect([switchPath('/diary'), switchPath('/es/diario'), switchPath('/account'), switchPath('/es/cuenta')])
      .toEqual(['/es/diario', '/diary', '/es/cuenta', '/account']);
  });

  it('has a pair for every page except the 404 pages, and every pair is a page', () => {
    const paths = allPagePaths();
    for (const p of paths) {
      if (!p.endsWith('/404') && !(p in PRIVATE_PAIRS)) expect(Object.keys(pairs)).toContain(p);
      expect(paths).toContain(switchPath(p));
    }
  });

  it('builds card addresses from the slugs', () => {
    const moon = DECK.find((c) => c.card_id === 'major-18-moon')!;
    expect(cardPath(moon, 'en')).toBe('/cards/the-moon');
    expect(cardPath(moon, 'es')).toBe('/es/cartas/la-luna');
  });

  it('knows the language of an address', () => {
    expect(langOf('/es')).toBe('es');
    expect(langOf('/es#una-carta')).toBe('es');
    expect(langOf('/es/cartas/la-luna')).toBe('es');
    expect(langOf('/espanol')).toBe('en');
    expect(langOf('/')).toBe('en');
  });

  it('has the four menu items of 4.4a in both languages', () => {
    expect(NAV_KEYS).toEqual(['home', 'yes_no', 'love', 'daily']);
    expect(NAV_KEYS.map((k) => pagePath(k, 'es'))).toEqual(['/es', '/es/si-o-no', '/es/amor', '/es/carta-del-dia']);
  });

  it('keeps the diary and the account out of hreflang.csv (noindex pages)', () => {
    for (const p of Object.keys(PRIVATE_PAIRS)) expect(Object.keys(pairs)).not.toContain(p);
  });

  it('names the file the static build writes for each address', () => {
    expect(distFile('/')).toBe('index.html');
    expect(distFile('/one-card')).toBe('one-card.html');
    expect(distFile('/es')).toBe('es.html');
    expect(distFile('/es/404')).toBe('es/404.html');
    expect(distFile('/es/cartas/la-luna')).toBe('es/cartas/la-luna.html');
  });
});
