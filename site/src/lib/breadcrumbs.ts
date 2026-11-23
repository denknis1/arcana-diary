// Breadcrumbs (spec stage 6 §3; stage 2 `breadcrumb` columns): first Home / Inicio; a major card — Home › Cards ›
// Major Arcana › card; a minor card — Home › Cards › card; the hub — Home › Cards; Major Arcana — Home › Cards › Major
// Arcana; the yes/no card list — Home › Yes or No › Card list; "3 cartas" — Inicio › 3 cartas; the tools on the home
// level have none.
import { t } from '../i18n';
import { cardName, type DeckCard } from './deck';
import { cardPath, pagePath, type PageKey } from './routes';
import type { Lang } from './types';

export interface Crumb {
  name: string;
  path: string;
}

function base(lang: Lang): { home: Crumb; cards: Crumb; major: Crumb } {
  const d = t(lang);
  return {
    home: { name: d.crumbHome, path: pagePath('home', lang) },
    cards: { name: d.crumbCards, path: pagePath('cards', lang) },
    major: { name: d.crumbMajor, path: pagePath('major_arcana', lang) },
  };
}

export function crumbsFor(key: PageKey, lang: Lang): Crumb[] {
  const d = t(lang);
  const { home, cards, major } = base(lang);
  switch (key) {
    case 'cards':
      return [home, cards];
    case 'major_arcana':
      return [home, cards, major];
    case 'yes_no_cards':
      return [home, { name: d.navYesNo, path: pagePath('yes_no', lang) },
        { name: d.crumbYesNoCards, path: pagePath('yes_no_cards', lang) }];
    case 'three_cards':
      return [home, { name: d.threeCardsChip, path: pagePath('three_cards', lang) }];
    default:
      return [];
  }
}

export function cardCrumbs(card: DeckCard, lang: Lang): Crumb[] {
  const { home, cards, major } = base(lang);
  const self = { name: cardName(card, lang), path: cardPath(card, lang) };
  return card.arcana === 'major' ? [home, cards, major, self] : [home, cards, self];
}
