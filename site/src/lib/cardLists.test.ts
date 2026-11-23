import { describe, expect, it } from 'vitest';
import { SUITS, firstKeyword, ldItems, majorCards, suitCards, verdictCards } from './cardLists';
import { cardById } from './deck';
import { FACTS } from './facts';

describe('card lists of the hubs (spec stage 6 §5: from the data, not from the text)', () => {
  it('list the 22 Major Arcana in deck order with their addresses', () => {
    const majors = majorCards('en');
    expect(majors).toHaveLength(22);
    expect(majors[0]).toMatchObject({ name: 'The Fool', href: '/cards/the-fool' });
    expect(majorCards('es')[21]).toMatchObject({ name: 'El Mundo', href: '/es/cartas/el-mundo' });
  });

  it('list 14 cards in each of the four suits', () => {
    expect(SUITS).toEqual(['wands', 'cups', 'swords', 'pentacles']);
    for (const suit of SUITS) expect(suitCards(suit, 'en')).toHaveLength(14);
    expect(suitCards('swords', 'es')[2]).toMatchObject({ name: 'Tres de Espadas', href: '/es/cartas/tres-de-espadas' });
  });

  it('sort the deck by its yes/no verdict, as many as the facts say', () => {
    expect(verdictCards('yes', 'en')).toHaveLength(Number(FACTS.yes_count));
    expect(verdictCards('no', 'en')).toHaveLength(Number(FACTS.no_count));
    expect(verdictCards('unclear', 'en').map((c) => c.name)).toContain('The Moon');
  });

  it('give each card its first keyword and the JSON-LD items', () => {
    expect(firstKeyword(cardById('major-18-moon')!, 'en')).toBe('uncertainty');
    expect(firstKeyword(cardById('major-00-fool')!, 'es')).toBe('comienzo');
    expect(ldItems(majorCards('en')).slice(0, 1)).toEqual([{ name: 'The Fool', path: '/cards/the-fool' }]);
  });
});
