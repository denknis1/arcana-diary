import { describe, expect, it } from 'vitest';
import {
  SECTION_IDS, aboutLines, ctaText, factsLine, faqHeading, formatDate, formatPages, imageCaption, keywordCaption,
  keywordRows, mentionSegments, pairRows, relatedCards, segmentsOf, titleParts, tocLinks, waiteCite, yesNoLines,
  yesNoReason,
} from './cardPage';
import { CARD_PAGES, TEMPLATE_STRINGS, cardPage } from './cardPages';
import { cardById, cardName } from './deck';
import { cardPath } from './routes';
import meaningsEn from '../data/meanings.en.json';

// Owner-reviewed text (the card pages, the card meanings) is read from the loaded JSON, so an edit or a re-review of
// a page keeps the suite green; literals stay only for the formats the template adds.

const EN = TEMPLATE_STRINGS.en;
const ES = TEMPLATE_STRINGS.es;
const moon = cardById('major-18-moon')!;
const swords3 = cardById('swords-03-three')!;
const lovers = cardById('major-06-lovers')!;
const moonEn = cardPage(moon, 'en');
const why = (id: string) => meaningsEn.find((m) => m.card_id === id)!.yes_no_why;

describe('the card template (spec stage 6 §4, rules §12)', () => {
  it('writes the facts line, linking the suit of a minor card to its block on the hub', () => {
    expect(factsLine(cardPage(moon, 'en'), EN, 'en')).toEqual({ before: 'Major Arcana · card XVIII', link: null, after: '' });
    expect(factsLine(cardPage(swords3, 'en'), EN, 'en')).toEqual({ before: 'Minor Arcana · ',
      link: { text: 'Swords', href: '/cards#swords' }, after: ' · Three' });
    expect(factsLine(cardPage(swords3, 'es'), ES, 'es')).toEqual({ before: 'Arcanos menores · ',
      link: { text: 'Espadas', href: '/es/cartas#espadas' }, after: ' · Tres' });
    const loversEs = cardPage(lovers, 'es');
    expect(loversEs.facts.also_called.length).toBeGreaterThan(0);
    expect(factsLine(loversEs, ES, 'es').after).toBe(loversEs.facts.also_called.map((n) => ` · ${n}`).join(''));
  });

  it('captions the scan and the keyword table, one row per orientation with no empty cell', () => {
    expect(imageCaption(cardPage(moon, 'en'), EN)).toBe('The Moon, 1909 Rider–Waite–Smith deck ("Roses & Lilies" '
      + 'printing), drawn by Pamela Colman Smith. Public-domain scan, Wikimedia Commons.');
    expect(keywordCaption(cardPage(moon, 'es'), ES)).toBe('La Luna: palabras clave');
    expect(keywordRows(moonEn, EN)).toEqual([
      { label: 'Upright', words: moonEn.keywords.upright.join(', ') },
      { label: 'Reversed', words: moonEn.keywords.reversed.join(', ') }]);
    for (const page of CARD_PAGES) {
      for (const row of keywordRows(page, TEMPLATE_STRINGS[page.lang])) {
        expect(row.words, `${page.lang}/${page.card_id}`).not.toBe('');
      }
    }
  });

  it('cites Waite with the page list of the edition', () => {
    expect(formatPages([286], EN)).toBe('p. 286');
    expect(formatPages([140, 143], ES)).toBe('pp. 140, 143');
    expect(waiteCite(moonEn, EN)).toBe(`A. E. Waite, The Pictorial Key to the Tarot (1911), ${formatPages(moonEn.waite.pages, EN)}`);
    expect(titleParts(waiteCite(moonEn, EN))).toEqual({ before: 'A. E. Waite, ', title: 'The Pictorial Key to the Tarot',
      after: ` (1911), ${formatPages(moonEn.waite.pages, EN)}` });
    expect(titleParts('plain')).toEqual({ before: 'plain', title: null, after: '' });
  });

  it('builds the yes/no lines from the deck verdict and the reason of the card base', () => {
    expect(yesNoReason(moon, 'en')).toBe(why(moon.card_id));
    expect(yesNoLines(moon, yesNoReason(moon, 'en'), EN, 'en')).toEqual({
      upright: `Upright: Not clear yet. ${why(moon.card_id)}`, reversed: 'Reversed: Not clear yet.', rule: EN.yes_no.rule });
    expect(yesNoLines(swords3, yesNoReason(swords3, 'en'), EN, 'en').upright).toBe(`Upright: No. ${why(swords3.card_id)}`);
    expect(yesNoLines(moon, yesNoReason(moon, 'es'), ES, 'es').reversed).toBe('Al revés: Todavía no está claro.');
  });

  it('names both cards of a pair and links the other one', () => {
    const pairs = moonEn.blocks.find((b) => b.id === 'combinations')!.pairs!;
    expect(pairRows(moonEn, EN, 'en')).toEqual(pairs.map((pair) => {
      const other = cardById(pair.card_id)!;
      return { before: 'The Moon + ', link: { text: cardName(other, 'en'), href: cardPath(other, 'en') }, after: '',
        reading: pair.text };
    }));
    const other = cardById(pairs[0].card_id)!;
    expect(pairRows(cardPage(moon, 'es'), ES, 'es')[0].link).toEqual({ text: cardName(other, 'es'), href: cardPath(other, 'es') });
  });

  it('links the first mention of another card, in the blocks or in the FAQ answers', () => {
    let faqLinks = 0;
    for (const page of CARD_PAGES) {
      const map = mentionSegments(page, page.lang);
      for (const mention of page.mentions) {
        const c = cardById(mention.card_id)!;
        const hits = [...map.entries()].filter(([, segs]) => segs.some((seg) => typeof seg !== 'string'
          && seg.text === mention.text && seg.href === cardPath(c, page.lang)));
        expect(hits.length, `${page.lang}/${page.card_id}: ${mention.text}`).toBeGreaterThan(0);
        if (hits.some(([key]) => key.startsWith('faq:'))) faqLinks += 1;
      }
      const texts = new Map<string, string>([['capsule', page.capsule],
        ...page.blocks.flatMap((b) => (b.paragraphs ?? []).map((p, j): [string, string] => [`${b.id}:${j}`, p])),
        ...page.faq.map((f, i): [string, string] => [`faq:${i}`, f.a])]);
      for (const [key, segs] of map) {
        expect(segs.map((seg) => (typeof seg === 'string' ? seg : seg.text)).join('')).toBe(texts.get(key));
      }
    }
    expect(faqLinks).toBeGreaterThan(0);
    expect(segmentsOf(new Map(), 'capsule', 'plain')).toEqual(['plain']);
  });

  it('finds every mention and every pair of all 156 pages, each page reviewed with a date', () => {
    for (const page of CARD_PAGES) {
      const s = TEMPLATE_STRINGS[page.lang];
      const links = [...mentionSegments(page, page.lang).values()].flat().filter((seg) => typeof seg !== 'string');
      expect(links, `${page.lang}/${page.card_id}`).toHaveLength(page.mentions.length);
      expect(pairRows(page, s, page.lang).length).toBeGreaterThanOrEqual(3);
      expect(relatedCards(page).length).toBe(page.related.length);
      expect(page.reviewed_at).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }
  });

  it('heads the CTA and the FAQ with the name in the sentence', () => {
    const swords3En = cardPage(swords3, 'en');
    expect(ctaText(swords3En, EN).heading).toBe(`Draw ${swords3En.name_forms.in_sentence} for your question`);
    expect(ctaText(cardPage(moon, 'es'), ES).heading).toBe('¿Qué dice La Luna de tu pregunta?');
    expect(faqHeading(moonEn, EN)).toBe('Questions about The Moon');
  });

  it('signs the page with the editor and the date of the review', () => {
    expect(formatDate('2026-11-23', 'en')).toBe('November 23, 2026');
    expect(formatDate('2026-11-23', 'es')).toBe('23 de noviembre de 2026');
    const about = aboutLines(moonEn, EN, 'en', 'Adrian Solenne');
    expect(about.method).toBe("Written with AI from Waite's book and Arcana Diary's card meanings. Reviewed by "
      + `Adrian Solenne on ${formatDate(moonEn.reviewed_at!, 'en')}.`);
    expect(about.sources).toEqual(moonEn.sources.map((src) => ({ what: src.what, where: src.where,
      pages: src.pages ? `${src.pages.length === 1 ? 'p.' : 'pp.'} ${src.pages.join(', ')}` : null, url: src.url })));
    expect(about.sources.find((_, i) => moonEn.sources[i].kind === 'project')!.url).toBeNull();
  });

  it('gives the sections the anchors of the page maps (EN #reversed; ES #invertida, #amor, #si-o-no)', () => {
    expect([SECTION_IDS.en.reversed, SECTION_IDS.en.love]).toEqual(['reversed', 'love']);
    expect([SECTION_IDS.es.reversed, SECTION_IDS.es.love, SECTION_IDS.es.yes_no]).toEqual(['invertida', 'amor', 'si-o-no']);
    expect(tocLinks('es')).toEqual([{ href: '#al-derecho', label: 'Al derecho' }, { href: '#invertida', label: 'Al revés' },
      { href: '#amor', label: 'Amor' }, { href: '#trabajo-y-dinero', label: 'Trabajo y dinero' },
      { href: '#si-o-no', label: 'Sí o no' }, { href: '#preguntas', label: 'Preguntas' }]);
  });
});
