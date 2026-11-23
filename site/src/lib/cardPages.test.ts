import { describe, expect, it } from 'vitest';
import { CARD_BLOCK_IDS, CARD_PAGES, TEMPLATE_STRINGS, cardPage } from './cardPages';
import { DECK, cardById } from './deck';

describe('card pages (schema 2)', () => {
  it('cover the deck in both languages with the 12 blocks in order', () => {
    expect(CARD_PAGES).toHaveLength(156);
    for (const lang of ['en', 'es'] as const) {
      for (const card of DECK) expect(cardPage(card, lang).blocks.map((b) => b.id)).toEqual(CARD_BLOCK_IDS);
    }
  });

  it('find a page by card and language', () => {
    const moon = cardById('major-18-moon')!;
    expect(cardPage(moon, 'en').h1).toBe('The Moon Tarot Card Meaning');
    expect(cardPage(moon, 'es').name_forms.de).toBe('de La Luna');
    expect(cardPage(moon, 'es').waite.translation).toMatch(/^Enemigos ocultos/);
  });

  it('carry the template strings of both languages with the same keys', () => {
    expect(TEMPLATE_STRINGS.en.waite.translation_label).toBeNull();
    expect(TEMPLATE_STRINGS.es.waite.translation_label).toBe('Traducción nuestra');
    expect(Object.keys(TEMPLATE_STRINGS.es).sort()).toEqual(Object.keys(TEMPLATE_STRINGS.en).sort());
  });
});
