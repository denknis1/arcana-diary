import { describe, expect, it } from 'vitest';
import { FACTS } from './facts';
import { SERVICE_PAGE_IDS, TEXT_PAGES, filledPage, hiddenPaths, isHidden, pageTexts, textPage } from './textPages';

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

  it('hide a service page while an operator placeholder has no value (owner decision 35)', () => {
    expect(isHidden(textPage('/about'))).toBe(true);
    expect(isHidden(textPage('/es/privacidad'))).toBe(true);
    expect(isHidden(textPage('/how-readings-work'))).toBe(false);
    expect(isHidden(textPage('/'))).toBe(false);
    expect(isHidden(textPage('/about'), { ...FACTS, operator_name: 'X', operator_address: 'Y', contact_email: 'Z' }))
      .toBe(false);
  });

  it('refuse a page that is not a service page and has a placeholder without a value', () => {
    const page = { ...textPage('/'), capsule: 'Up to {nope} cards' };
    expect(() => isHidden(page)).toThrow('{nope}');
  });

  it('know the ten service pages and which of them are hidden now', () => {
    expect(SERVICE_PAGE_IDS.size).toBe(10);
    expect([...hiddenPaths()].sort()).toEqual(['/about', '/contact', '/es/contacto', '/es/privacidad',
      '/es/sobre-nosotros', '/es/terminos', '/privacy', '/terms']);
  });
});
