// The draw panel of each page (spec 4.4a §3): which kind it draws, which choices it offers, the button label and
// the body of POST /api/readings. One place for every page, so the pages only name themselves.
import type { DictKey } from '../i18n';
import type { CardCount, CreateBody, Kind, Lang, Situation, Tool } from './types';

export type PanelPage = 'home' | 'one_card' | 'yes_no' | 'love' | 'card' | 'three_cards';

export interface PanelConfig {
  page: PanelPage;
  lang: Lang;
  tool: Tool;
  entry: 'tool' | 'card_page';
  kind: Kind; // the kind drawn when nothing else is chosen
  countToggle: boolean; // Spanish home: "1 carta / 3 cartas" (one or three kind)
  yesNoCount: boolean; // yes/no: "1 card / 3 cards", the same kind on one or three cards (spec 4.5 §4)
  situations: boolean; // love: the situation chips
  topic: 'love' | null;
  cardId: string | null; // a card page: the card it is drawn from
  labelKey: DictKey;
  placeholderKey: DictKey;
}

export const ONE_CARD_ANCHOR = '#una-carta';
export const QUESTION_MAX = 500;

export function panelConfig(page: PanelPage, lang: Lang, cardId: string | null = null): PanelConfig {
  const base = { page, lang, entry: 'tool' as const, countToggle: false, yesNoCount: false, situations: false, topic: null,
    cardId: null, labelKey: 'questionLabel' as DictKey };
  switch (page) {
    case 'home':
      return { ...base, tool: 'home', kind: 'three', countToggle: lang === 'es', placeholderKey: 'homePlaceholder' };
    case 'one_card':
      return { ...base, tool: 'one_card', kind: 'one', placeholderKey: 'oneCardPlaceholder' };
    case 'yes_no':
      return { ...base, tool: 'yes_no', kind: 'yes_no', yesNoCount: true, labelKey: 'yesNoLabel', placeholderKey: 'yesNoPlaceholder' };
    case 'love':
      return { ...base, tool: 'love', kind: 'three', situations: true, topic: 'love', placeholderKey: 'lovePlaceholder' };
    case 'three_cards': // /es/tiradas/3-cartas (spec stage 6 §5): past, present, where it's heading
      return { ...base, tool: 'three_cards', kind: 'three', placeholderKey: 'homePlaceholder' };
    case 'card':
      return { ...base, tool: 'one_card', entry: 'card_page', kind: 'card_page', cardId, placeholderKey: 'cardPlaceholder' };
  }
}

/** The kind on load: the Spanish home opened at #una-carta starts with one card. */
export function initialKind(config: PanelConfig, hash: string): Kind {
  return config.countToggle && hash === ONE_CARD_ANCHOR ? 'one' : config.kind;
}

export function drawLabelKey(config: PanelConfig, kind: Kind, count: CardCount = 1): DictKey {
  if (config.page === 'card') return 'drawForQuestion';
  if (config.page === 'love') return 'drawLove';
  return cardsFor(kind, count) === 3 ? 'drawThree' : 'drawOne';
}

/** The tool an event names: one card drawn on the Spanish home counts as one card (plan review M9). */
export function toolFor(config: PanelConfig, kind: Kind): Tool {
  return config.countToggle && kind === 'one' ? 'one_card' : config.tool;
}

/** The cards a draw deals: three for `three`, and for yes/no the chosen count. */
export function cardsFor(kind: Kind, count: CardCount = 1): CardCount {
  return kind === 'three' || (kind === 'yes_no' && count === 3) ? 3 : 1;
}

export function cleanQuestion(question: string): string {
  return Array.from(question.trim()).slice(0, QUESTION_MAX).join('');
}

export function buildCreateBody(config: PanelConfig, input: { kind: Kind; question: string; situation: Situation | null;
  tz: string | undefined; count?: CardCount }): CreateBody {
  const body: CreateBody = { lang: config.lang, kind: input.kind };
  if (config.yesNoCount) body.count = input.count ?? 1;
  const question = cleanQuestion(input.question);
  if (question) body.question = question;
  if (config.topic) body.topic = config.topic;
  if (config.situations && input.situation) body.situation = input.situation;
  if (config.cardId) body.card_id = config.cardId;
  if (input.tz) body.tz = input.tz;
  return body;
}

export function situationKey(situation: Situation): DictKey {
  const keys: Record<Situation, DictKey> = {
    single: 'sitSingle', relationship: 'sitRelationship', after_breakup: 'sitAfterBreakup', complicated: 'sitComplicated',
  };
  return keys[situation];
}
