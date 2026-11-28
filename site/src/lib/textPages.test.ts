import { describe, expect, it } from 'vitest';
import { FACTS } from './facts';
import { allPagePaths, hreflangPair } from './routes';
import { SERVICE_PAGE_IDS, TEXT_PAGES, filledPage, hiddenPaths, isHidden, openPagePath, pageTexts, textPage } from './textPages';

describe('stage 5 text pages', () => {
  it('are the 25 files of content/pages, one per address', () => {
    expect(TEXT_PAGES).toHaveLength(25);
    expect(new Set(TEXT_PAGES.map((p) => p.url)).size).toBe(25);
    expect(textPage('/cards').h1).toBe('Tarot card meanings: the whole deck, card by card');
    expect(textPage('/es/tiradas/3-cartas').lang).toBe('es');
    expect(() => textPage('/nope')).toThrow('/nope');
  });

  it('fill every placeholder of a page with the facts', () => {
    const home = filledPage(textPage('/'));
    expect(home.faq[0].a).toContain(`draw ${FACTS.guest_limit} readings a day`);
    expect(pageTexts(home).join(' ')).not.toMatch(/\{\w+\}/);
  });

  // a synthetic facts object: the real one is complete, the hide rule must still hold for an empty placeholder
  const { operator_name: _name, ...EMPTY_NAME } = FACTS;

  it('hide a service page while an operator placeholder has no value (owner decision 35)', () => {
    expect(isHidden(textPage('/about'), EMPTY_NAME)).toBe(true);
    expect(isHidden(textPage('/es/privacidad'), EMPTY_NAME)).toBe(true);
    expect(isHidden(textPage('/how-readings-work'), EMPTY_NAME)).toBe(false);
    expect(isHidden(textPage('/'), EMPTY_NAME)).toBe(false);
    expect(isHidden(textPage('/about'), { ...EMPTY_NAME, operator_name: 'X' })).toBe(false);
  });

  it('open every service page once the operator facts are all filled in, with the date of its own language', () => {
    const filled = { ...FACTS, operator_name: 'N', operator_address: 'City, Country', jurisdiction: 'Country' };
    for (const id of SERVICE_PAGE_IDS) {
      const page = TEXT_PAGES.find((p) => p.page_id === id)!;
      expect(isHidden(page, filled), id).toBe(false);
      expect(pageTexts(filledPage(page, filled)).join(' '), id).not.toMatch(/\{\w+\}/);
    }
    expect(filledPage(textPage('/privacy'), filled).lead).toContain('Effective date: November 28, 2026.');
    expect(filledPage(textPage('/es/privacidad'), filled).lead).toContain('Vigente desde: 28 de noviembre de 2026.');
  });

  it('refuse a page that is not a service page and has a placeholder without a value', () => {
    const page = { ...textPage('/'), capsule: 'Up to {nope} cards' };
    expect(() => isHidden(page)).toThrow('{nope}');
  });

  it('know the ten service pages, all open with the real operator facts', () => {
    expect(SERVICE_PAGE_IDS.size).toBe(10);
    expect([...hiddenPaths()]).toEqual([]);
    for (const page of TEXT_PAGES.filter((p) => SERVICE_PAGE_IDS.has(p.page_id))) {
      expect(isHidden(page), page.url).toBe(false);
      expect(pageTexts(filledPage(page)).join(' '), page.url).not.toMatch(/\{\w+\}/);
    }
  });

  it('hide exactly the eight operator pages with a synthetic empty operator name', () => {
    expect([...hiddenPaths(EMPTY_NAME)].sort()).toEqual(['/about', '/contact', '/es/contacto', '/es/privacidad',
      '/es/sobre-nosotros', '/es/terminos', '/privacy', '/terms']);
  });

  it('never pair an open page with a hidden one for hreflang', () => {
    for (const hidden of [hiddenPaths(), hiddenPaths(EMPTY_NAME)]) {
      for (const path of allPagePaths()) {
        const pair = hreflangPair(path);
        if (!hidden.has(path) && pair !== null) expect(hidden.has(pair), `${path} ↔ ${pair}`).toBe(false);
      }
    }
  });

  it('give the address of a hidden page once the set no longer holds it (injected)', () => {
    expect(openPagePath('privacy', 'en', new Set())).toBe('/privacy');
    expect(openPagePath('privacy', 'es', new Set(['/privacy']))).toBe('/es/privacidad');
    expect(openPagePath('privacy', 'en', new Set(['/privacy']))).toBeNull();
  });

  it('give the address of a page only while it is open', () => {
    expect(openPagePath('privacy', 'en')).toBe('/privacy');
    expect(openPagePath('privacy', 'es')).toBe('/es/privacidad');
    expect(openPagePath('how_readings_work', 'es')).toBe('/es/como-funcionan-las-lecturas');
  });
});
