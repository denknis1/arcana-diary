// What the card template adds to the stage 5 text (spec stage 6 §4, rules 30-card-page-rules.md §12): the facts
// line, the captions, the keyword rows, the Waite citation, the yes/no lines from the deck, the pairs, links on the
// first mention of another card, the CTA and FAQ headings and the "About this page" lines. Strings come only from
// template-strings.json and the dictionaries.
import { fill, t, type DictKey } from '../i18n';
import meaningsEn from '../data/meanings.en.json';
import meaningsEs from '../data/meanings.es.json';
import type { CardBlockId, CardPageData, TemplateStrings } from './cardPages';
import { cardById, cardName, type DeckCard } from './deck';
import { cardPath, suitPath } from './routes';
import type { Lang, Vote } from './types';

export type Segment = string | { text: string; href: string };

export interface LinkSlot {
  before: string;
  link: { text: string; href: string } | null;
  after: string;
}

export interface PairRow extends LinkSlot {
  reading: string;
}

type SectionKey = CardBlockId | 'draw' | 'faq' | 'related' | 'about';

/** Section anchors; EN #reversed, ES #invertida, #amor, #si-o-no are rows EN-095, ES-092…094 of the page maps. */
export const SECTION_IDS: Readonly<Record<Lang, Readonly<Record<SectionKey, string>>>> = {
  en: {
    on_the_card: 'on-the-card', waite: 'waite', upright: 'upright', reversed: 'reversed', love: 'love',
    work_money: 'work-and-money', advice: 'advice', yes_no: 'yes-or-no', in_a_reading: 'as-a-person',
    combinations: 'combinations', not_to_confuse: 'not-to-confuse', ask_yourself: 'ask-yourself',
    draw: 'draw', faq: 'faq', related: 'related', about: 'about',
  },
  es: {
    on_the_card: 'en-la-carta', waite: 'waite', upright: 'al-derecho', reversed: 'invertida', love: 'amor',
    work_money: 'trabajo-y-dinero', advice: 'consejo', yes_no: 'si-o-no', in_a_reading: 'como-persona',
    combinations: 'combinaciones', not_to_confuse: 'no-confundir', ask_yourself: 'preguntas-para-ti',
    draw: 'tu-pregunta', faq: 'preguntas', related: 'relacionadas', about: 'sobre-esta-pagina',
  },
};

const TOC: readonly [SectionKey, DictKey][] = [['upright', 'tocUpright'], ['reversed', 'tocReversed'], ['love', 'tocLove'],
  ['work_money', 'tocWorkMoney'], ['yes_no', 'tocYesNo'], ['faq', 'tocFaq']];

const VOTE_KEYS: Readonly<Record<Vote, DictKey>> = { yes: 'voteYes', no: 'voteNo', unclear: 'voteUnclear' };

const REASONS: Readonly<Record<Lang, ReadonlyMap<string, string>>> = {
  en: new Map(meaningsEn.map((m) => [m.card_id, m.yes_no_why])),
  es: new Map(meaningsEs.map((m) => [m.card_id, m.yes_no_why])),
};

const names = (page: CardPageData) => ({ Card: page.name_forms.name, card: page.name_forms.in_sentence });

/** The parts of a template around one placeholder, each filled with the other values. */
function around(template: string, key: string, vars: Readonly<Record<string, string>>): [string, string] {
  const [before, after = ''] = template.split(`{${key}}`);
  return [fill(before, vars), fill(after, vars)];
}

function card(cardId: string, page: CardPageData): DeckCard {
  const found = cardById(cardId);
  if (!found) throw new Error(`${page.lang}/${page.card_id}: unknown card ${cardId}`);
  return found;
}

export function formatPages(pages: readonly number[], s: TemplateStrings): string {
  return fill(pages.length === 1 ? s.about.page_one : s.about.page_many, { pages: pages.join(', ') });
}

export function formatDate(iso: string, lang: Lang): string {
  return new Intl.DateTimeFormat(lang === 'en' ? 'en-US' : 'es-MX', { dateStyle: 'long', timeZone: 'UTC' })
    .format(new Date(`${iso}T00:00:00Z`));
}

export function factsLine(page: CardPageData, s: TemplateStrings, lang: Lang): LinkSlot {
  const alsoCalled = page.facts.also_called.map((name) => ` · ${name}`).join('');
  if (page.facts.arcana === 'major' || page.facts.suit === null) {
    return { before: fill(s.facts.major, { numeral: page.facts.numeral ?? '' }), link: null, after: alsoCalled };
  }
  const [before, after] = around(s.facts.minor, 'suit', { rank: s.facts.ranks[String(page.facts.number)] });
  return { before, link: { text: s.facts.suits[page.facts.suit], href: suitPath(page.facts.suit, lang) },
    after: after + alsoCalled };
}

export function imageCaption(page: CardPageData, s: TemplateStrings): string {
  return fill(s.image_caption, names(page));
}

export function keywordCaption(page: CardPageData, s: TemplateStrings): string {
  return fill(s.keywords.caption, names(page));
}

/** One row per orientation (label, then all its keywords): no empty cells when the lists differ in length. */
export function keywordRows(page: CardPageData, s: TemplateStrings): { label: string; words: string }[] {
  return [
    { label: s.keywords.upright, words: page.keywords.upright.join(', ') },
    { label: s.keywords.reversed, words: page.keywords.reversed.join(', ') },
  ];
}

/** The title of Waite's book, marked as an English <cite> inside the citation and the Sources line. */
export const WAITE_TITLE = 'The Pictorial Key to the Tarot';

export function titleParts(text: string): { before: string; title: string | null; after: string } {
  const at = text.indexOf(WAITE_TITLE);
  if (at < 0) return { before: text, title: null, after: '' };
  return { before: text.slice(0, at), title: WAITE_TITLE, after: text.slice(at + WAITE_TITLE.length) };
}

export function waiteCite(page: CardPageData, s: TemplateStrings): string {
  return fill(s.waite.cite, { pages: formatPages(page.waite.pages, s) });
}

export function yesNoReason(c: DeckCard, lang: Lang): string {
  return REASONS[lang].get(c.card_id) ?? '';
}

/** Upright: the base verdict and its reason; reversed: always "Not clear yet" (yes-no-rules.json reversed_shift). */
export function yesNoLines(c: DeckCard, reason: string, s: TemplateStrings, lang: Lang) {
  const d = t(lang);
  return {
    upright: fill(s.yes_no.upright, { label: d[VOTE_KEYS[c.yes_no]], reason }),
    reversed: fill(s.yes_no.reversed, { label_reversed: d.voteUnclear }),
    rule: s.yes_no.rule,
  };
}

export function pairRows(page: CardPageData, s: TemplateStrings, lang: Lang): PairRow[] {
  const pairs = page.blocks.find((b) => b.id === 'combinations')?.pairs ?? [];
  return pairs.map((pair) => {
    const other = card(pair.card_id, page);
    const [before, after] = around(s.combinations.pair, 'Other', names(page));
    return { before, link: { text: cardName(other, lang), href: cardPath(other, lang) }, after, reading: pair.text };
  });
}

/** The page's running texts in reading order: capsule, block paragraphs, FAQ answers. */
function runningTexts(page: CardPageData): [string, string][] {
  return [
    ['capsule', page.capsule],
    ...page.blocks.flatMap((b) => (b.paragraphs ?? []).map((p, j): [string, string] => [`${b.id}:${j}`, p])),
    ...page.faq.map((f, i): [string, string] => [`faq:${i}`, f.a]),
  ];
}

/** `mentions`: the first place each mention's text appears (and is not taken by another mention) becomes a link. */
export function mentionSegments(page: CardPageData, lang: Lang): Map<string, Segment[]> {
  const texts = runningTexts(page);
  const claimed = new Map<string, { start: number; end: number; href: string }[]>();
  for (const mention of page.mentions) {
    const href = cardPath(card(mention.card_id, page), lang);
    let placed = false;
    for (const [key, text] of texts) {
      const taken = claimed.get(key) ?? [];
      for (let at = text.indexOf(mention.text); at >= 0 && !placed; at = text.indexOf(mention.text, at + 1)) {
        const end = at + mention.text.length;
        if (taken.every((r) => end <= r.start || at >= r.end)) {
          claimed.set(key, [...taken, { start: at, end, href }]);
          placed = true;
        }
      }
      if (placed) break;
    }
    if (!placed) throw new Error(`${page.lang}/${page.card_id}: mention "${mention.text}" is not in the text`);
  }
  const out = new Map<string, Segment[]>();
  for (const [key, text] of texts) {
    const ranges = [...(claimed.get(key) ?? [])].sort((a, b) => a.start - b.start);
    if (ranges.length === 0) continue;
    const segments: Segment[] = [];
    let at = 0;
    for (const r of ranges) {
      if (r.start > at) segments.push(text.slice(at, r.start));
      segments.push({ text: text.slice(r.start, r.end), href: r.href });
      at = r.end;
    }
    if (at < text.length) segments.push(text.slice(at));
    out.set(key, segments);
  }
  return out;
}

export function segmentsOf(map: ReadonlyMap<string, Segment[]>, key: string, text: string): Segment[] {
  return map.get(key) ?? [text];
}

export function ctaText(page: CardPageData, s: TemplateStrings): { heading: string; text: string } {
  return { heading: fill(s.cta.heading, names(page)), text: fill(s.cta.text, names(page)) };
}

export function faqHeading(page: CardPageData, s: TemplateStrings): string {
  return fill(s.faq.heading, names(page));
}

export function relatedCards(page: CardPageData): DeckCard[] {
  return page.related.map((id) => card(id, page));
}

export function tocLinks(lang: Lang): { href: string; label: string }[] {
  const d = t(lang);
  return TOC.map(([key, label]) => ({ href: `#${SECTION_IDS[lang][key]}`, label: d[label] }));
}

export function aboutLines(page: CardPageData, s: TemplateStrings, lang: Lang, editorName: string) {
  if (!page.reviewed_at) throw new Error(`${page.lang}/${page.card_id}: not reviewed`);
  return {
    sources: page.sources.map((src) => ({ what: src.what, where: src.where,
      pages: src.pages ? formatPages(src.pages, s) : null, url: src.url })),
    pageNumbers: s.about.page_numbers,
    method: fill(s.about.method, { editor_name: editorName, reviewed_at: formatDate(page.reviewed_at, lang) }),
    deckNote: s.about.deck_note,
  };
}
