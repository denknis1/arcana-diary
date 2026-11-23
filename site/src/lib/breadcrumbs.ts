// Breadcrumbs (spec stage 6 §3; stage 2 `breadcrumb` columns): first Home / Inicio; a major card — Home › Cards ›
// Major Arcana › card; a minor card — Home › Cards › card; the hub — Home › Cards; Major Arcana — Home › Cards › Major
// Arcana; the yes/no card list — Home › Yes or No › Card list; "3 cartas" — Inicio › 3 cartas; a service page — Home ›
// page; the tools on the home level have none.
import { t, type DictKey } from '../i18n';
import { cardName, type DeckCard } from './deck';
import { SERVICE_KEYS, cardPath, pagePath, type PageKey, type ServiceKey } from './routes';
import type { Lang } from './types';

export interface Crumb {
  name: string;
  path: string;
}

/** The short names of the service pages: the footer and the last breadcrumb. */
export const SERVICE_LABELS: Readonly<Record<ServiceKey, DictKey>> = {
  about: 'footerAbout', how_readings_work: 'footerHowReadings', contact: 'footerContact', privacy: 'footerPrivacy',
  terms: 'footerTerms',
};

const isService = (key: PageKey): key is ServiceKey => (SERVICE_KEYS as readonly PageKey[]).includes(key);

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
      if (lang !== 'en') return []; // no Spanish card list: the key is an alias of the yes/no tool
      return [home, { name: d.navYesNo, path: pagePath('yes_no', lang) },
        { name: d.crumbYesNoCards, path: pagePath('yes_no_cards', lang) }];
    case 'three_cards':
      if (lang !== 'es') return []; // no English three-card page: the key is an alias of the home page
      return [home, { name: d.threeCardsChip, path: pagePath('three_cards', lang) }];
    default:
      return isService(key) ? [home, { name: d[SERVICE_LABELS[key]], path: pagePath(key, lang) }] : [];
  }
}

export function cardCrumbs(card: DeckCard, lang: Lang): Crumb[] {
  const { home, cards, major } = base(lang);
  const self = { name: cardName(card, lang), path: cardPath(card, lang) };
  return card.arcana === 'major' ? [home, cards, major, self] : [home, cards, self];
}
