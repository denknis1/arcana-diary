import { describe, expect, it } from 'vitest';
import { cardCrumbs, crumbsFor } from './breadcrumbs';
import { cardById } from './deck';

describe('breadcrumbs (spec stage 6 §3)', () => {
  it('start with Home / Inicio and follow the stage 2 trails', () => {
    expect(crumbsFor('cards', 'en')).toEqual([{ name: 'Home', path: '/' }, { name: 'Cards', path: '/cards' }]);
    expect(crumbsFor('major_arcana', 'es')).toEqual([{ name: 'Inicio', path: '/es' }, { name: 'Cartas', path: '/es/cartas' },
      { name: 'Arcanos mayores', path: '/es/cartas/arcanos-mayores' }]);
    expect(crumbsFor('yes_no_cards', 'en')).toEqual([{ name: 'Home', path: '/' }, { name: 'Yes or No', path: '/yes-no' },
      { name: 'Card list', path: '/yes-no/cards' }]);
    expect(crumbsFor('three_cards', 'es')).toEqual([{ name: 'Inicio', path: '/es' },
      { name: '3 cartas', path: '/es/tiradas/3-cartas' }]);
  });

  it('give the tools on the home level no breadcrumbs', () => {
    for (const key of ['home', 'one_card', 'yes_no', 'love', 'daily'] as const) expect(crumbsFor(key, 'en')).toEqual([]);
  });

  it('put a major card under Major Arcana and a minor card under Cards', () => {
    expect(cardCrumbs(cardById('major-18-moon')!, 'en')).toEqual([{ name: 'Home', path: '/' },
      { name: 'Cards', path: '/cards' }, { name: 'Major Arcana', path: '/cards/major-arcana' },
      { name: 'The Moon', path: '/cards/the-moon' }]);
    expect(cardCrumbs(cardById('swords-03-three')!, 'es')).toEqual([{ name: 'Inicio', path: '/es' },
      { name: 'Cartas', path: '/es/cartas' }, { name: 'Tres de Espadas', path: '/es/cartas/tres-de-espadas' }]);
  });

  it('gives no trail for an alias key (the page does not exist in that language)', () => {
    expect(crumbsFor('three_cards', 'en')).toEqual([]);
    expect(crumbsFor('yes_no_cards', 'es')).toEqual([]);
  });
});
