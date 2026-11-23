import { describe, expect, it } from 'vitest';
import pairs from '../data/pairs.json';
import { DECK } from './deck';
import { NAV_KEYS, PRIVATE_PAIRS, allPagePaths, cardPath, distFile, drawnCardLink, hreflangPair, langOf, pagePath, switchPath } from './routes';

describe('routes', () => {
  it('lists every page of the site for both languages (stage 6 part 1)', () => {
    const paths = allPagePaths();
    expect(paths).toHaveLength(16 + 78 + 15 + 78);
    for (const p of ['/', '/one-card', '/yes-no', '/love', '/daily', '/diary', '/account', '/404', '/es', '/es/si-o-no',
      '/es/amor', '/es/carta-del-dia', '/es/diario', '/es/cuenta', '/es/404', '/cards/the-moon', '/es/cartas/la-luna',
      '/cards', '/cards/major-arcana', '/yes-no/cards', '/es/cartas', '/es/cartas/arcanos-mayores',
      '/es/tiradas/3-cartas', '/about', '/how-readings-work', '/contact', '/privacy', '/terms', '/es/sobre-nosotros',
      '/es/como-funcionan-las-lecturas', '/es/contacto', '/es/privacidad', '/es/terminos']) {
      expect(paths).toContain(p);
    }
    expect(new Set(paths).size).toBe(paths.length);
  });

  it('maps the pages that exist in one language only onto the nearest page of the other', () => {
    expect(pagePath('three_cards', 'es')).toBe('/es/tiradas/3-cartas');
    expect(pagePath('three_cards', 'en')).toBe('/'); // the English home is the three-card reading
    expect(pagePath('yes_no_cards', 'en')).toBe('/yes-no/cards');
    expect(pagePath('yes_no_cards', 'es')).toBe('/es/si-o-no'); // no Spanish card list: the yes/no tool
  });

  it('pairs a page for hreflang only when its pair points back at it', () => {
    expect(hreflangPair('/yes-no')).toBe('/es/si-o-no');
    expect(hreflangPair('/es/si-o-no')).toBe('/yes-no');
    expect(hreflangPair('/cards')).toBe('/es/cartas');
    expect(hreflangPair('/cards/the-moon')).toBe('/es/cartas/la-luna');
    expect(hreflangPair('/one-card')).toBeNull();
    expect(hreflangPair('/yes-no/cards')).toBeNull();
    expect(hreflangPair('/es/tiradas/3-cartas')).toBeNull();
    expect(hreflangPair('/diary')).toBeNull();
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
    expect(switchPath('/cards')).toBe('/es/cartas');
    expect(switchPath('/yes-no/cards')).toBe('/es/si-o-no');
    expect(switchPath('/es/tiradas/3-cartas')).toBe('/');
    expect(switchPath('/404')).toBe('/es/404');
    expect(switchPath('/es/404')).toBe('/404');
    expect(switchPath('/about')).toBe('/es/sobre-nosotros');
    expect(switchPath('/es/terminos')).toBe('/terms');
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

  it('has the menu items of stage 6 in both languages (stage 2 menu table)', () => {
    expect(NAV_KEYS).toEqual(['home', 'yes_no', 'love', 'daily', 'cards', 'diary']);
    expect(NAV_KEYS.map((k) => pagePath(k, 'es'))).toEqual(['/es', '/es/si-o-no', '/es/amor', '/es/carta-del-dia',
      '/es/cartas', '/es/diario']);
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

describe('drawnCardLink (owner decision 38; every row on screen: NightRoom.test.tsx, DailyIsland.test.tsx)', () => {
  it('gives each tool its launch rows of the stage 2 matrix, in both languages', () => {
    const moon = { card_id: 'major-18-moon', reversed: false };
    const rows = (lang: 'en' | 'es') => (['home', 'one_card', 'three_cards', 'love', 'yes_no', 'daily'] as const)
      .map((tool) => drawnCardLink(moon, tool, lang).map((l) => l.row).join('+'));
    expect(rows('en')).toEqual(['L-EN-01', 'L-EN-02', 'L-EN-01', 'L-EN-03', 'L-EN-31', 'L-EN-15']);
    expect(rows('es')).toEqual(['L-ES-01', 'L-ES-01', 'L-ES-02', 'L-ES-03+L-ES-23', 'L-ES-04', 'L-ES-15']);
  });

  it('takes the vote from the API, else the yes/no rule (reversed: not clear yet); no link for an unknown card', () => {
    const sun = (reversed: boolean, vote?: 'no') => drawnCardLink({ card_id: 'major-19-sun', reversed, vote }, 'yes_no', 'es')[0].text;
    expect([sun(false), sun(true), sun(false, 'no')]).toEqual(['Por qué El Sol dice sí',
      'Por qué El Sol dice todavía no está claro', 'Por qué El Sol dice no']);
    expect(drawnCardLink({ card_id: 'major-99-none', reversed: false }, 'love', 'es')).toEqual([]);
  });
});
