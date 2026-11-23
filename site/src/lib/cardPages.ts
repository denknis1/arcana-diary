// The stage 5 card pages (content/cards/pages, schema 2; rules docs/research/stage5/30-card-page-rules.md §1, §12)
// and the strings the template adds to every one of them (template-strings.json), copied to src/data/cardpages by
// tools/site/sync_site_data.py without `citations` (the reviewer's excerpts).
import templateData from '../data/cardpages/template-strings.json';
import type { DeckCard } from './deck';
import type { FaqItem } from './textPages';
import type { Lang } from './types';

export type CardBlockId = 'on_the_card' | 'waite' | 'upright' | 'reversed' | 'love' | 'work_money' | 'advice' | 'yes_no'
  | 'in_a_reading' | 'combinations' | 'not_to_confuse' | 'ask_yourself';

export const CARD_BLOCK_IDS: readonly CardBlockId[] = ['on_the_card', 'waite', 'upright', 'reversed', 'love',
  'work_money', 'advice', 'yes_no', 'in_a_reading', 'combinations', 'not_to_confuse', 'ask_yourself'];

export interface CardPair {
  card_id: string;
  text: string;
}

export interface CardBlock {
  id: CardBlockId;
  heading: string;
  paragraphs?: string[]; // every block but combinations
  pairs?: CardPair[]; // combinations only
}

export interface CardSource {
  kind: 'image' | 'waite' | 'project';
  what: string;
  where: string;
  pages?: number[];
  url: string | null;
}

export interface CardPageData {
  schema: 2;
  card_id: string;
  lang: Lang;
  status: string;
  editor: string;
  reviewed_at: string | null;
  name_forms: { name: string; in_sentence: string; de?: string };
  title: string;
  description: string;
  h1: string;
  image_alt: string;
  facts: { arcana: 'major' | 'minor'; suit: 'wands' | 'cups' | 'swords' | 'pentacles' | null; number: number;
    numeral: string | null; also_called: string[] };
  capsule: string;
  keywords: { upright: string[]; reversed: string[] };
  blocks: CardBlock[];
  faq: FaqItem[];
  related: string[];
  mentions: { card_id: string; text: string }[];
  waite: { quote: string; quote_lang: 'en'; pages: number[]; translation: string | null; harsh: boolean };
  sources: CardSource[];
}

export interface TemplateStrings {
  facts: { major: string; minor: string; suits: Record<'wands' | 'cups' | 'swords' | 'pentacles', string>;
    ranks: Record<string, string> };
  image_caption: string;
  keywords: { caption: string; upright: string; reversed: string };
  waite: { cite: string; translation_label: string | null; harsh_context: string; boundary: string };
  work_money: { money_line: string };
  yes_no: { upright: string; reversed: string; rule: string };
  in_a_reading: { note: string };
  combinations: { intro: string; pair: string; col_pair: string; col_reading: string };
  ask_yourself: { diary_button: string };
  cta: { heading: string; text: string; button: string };
  faq: { heading: string };
  related: { heading: string };
  about: { heading: string; sources_label: string; page_one: string; page_many: string; page_numbers: string;
    method: string; deck_note: string };
}

export const TEMPLATE_STRINGS: Readonly<Record<Lang, TemplateStrings>> = {
  en: templateData.en as TemplateStrings,
  es: templateData.es as TemplateStrings,
};

const FILES = import.meta.glob<CardPageData>('../data/cardpages/*/*.json', { eager: true, import: 'default' });

export const CARD_PAGES: readonly CardPageData[] = Object.values(FILES);

const BY_KEY = new Map(CARD_PAGES.map((page) => [`${page.lang}/${page.card_id}`, page]));

export function cardPage(card: DeckCard, lang: Lang): CardPageData {
  const page = BY_KEY.get(`${lang}/${card.card_id}`);
  if (!page) throw new Error(`no card page ${lang}/${card.card_id} in src/data/cardpages`);
  return page;
}
