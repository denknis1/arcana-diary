import { describe, expect, it } from 'vitest';
import { CARD_BACK, DECK, cardById, cardImage, cardName, cardSlug, cardSrcset, fallbackDailyCard, neighbors } from './deck';

describe('deck', () => {
  it('has the 78 cards in deck order', () => {
    expect(DECK).toHaveLength(78);
    expect(DECK[0].card_id).toBe('major-00-fool');
    expect(new Set(DECK.map((c) => c.card_id)).size).toBe(78);
  });

  it('finds a card by id and names it in both languages', () => {
    const moon = cardById('major-18-moon')!;
    expect(cardName(moon, 'en')).toBe('The Moon');
    expect(cardName(moon, 'es')).toBe('La Luna');
    expect(cardSlug(moon, 'es')).toBe('la-luna');
    expect(moon.numeral).toBe('XVIII');
    expect(cardById('nope')).toBeUndefined();
  });

  it('builds the three picture sizes and the srcset', () => {
    const moon = cardById('major-18-moon')!;
    expect(cardImage(moon, 700)).toBe('/cards/the-moon.webp');
    expect(cardImage(moon, 160)).toBe('/cards/the-moon@160.webp');
    expect(cardSrcset(moon)).toBe('/cards/the-moon@160.webp 160w, /cards/the-moon@350.webp 350w, /cards/the-moon.webp 700w');
    expect(CARD_BACK).toBe('/cards/back.svg');
  });

  it('gives neighbours in deck order, wrapping at the ends', () => {
    const fool = DECK[0];
    expect(neighbors(fool).prev).toBe(DECK[77]);
    expect(neighbors(fool).next).toBe(DECK[1]);
    expect(neighbors(DECK[77]).next).toBe(fool);
  });

  it('picks the same fallback card of the day for the same day and changes with the day', () => {
    expect(fallbackDailyCard('2026-11-20')).toBe(fallbackDailyCard('2026-11-20'));
    const days = Array.from({ length: 30 }, (_, i) => `2026-12-${String(i + 1).padStart(2, '0')}`);
    expect(new Set(days.map((d) => fallbackDailyCard(d).card_id)).size).toBeGreaterThan(10);
  });
});
