import { describe, expect, it } from 'vitest';
import {
  SECTION_IDS, aboutLines, ctaText, factsLine, faqHeading, formatDate, formatPages, imageCaption, keywordCaption,
  keywordRows, mentionSegments, pairRows, relatedCards, segmentsOf, tocLinks, waiteCite, yesNoLines, yesNoReason,
} from './cardPage';
import { CARD_PAGES, TEMPLATE_STRINGS, cardPage } from './cardPages';
import { cardById } from './deck';

const EN = TEMPLATE_STRINGS.en;
const ES = TEMPLATE_STRINGS.es;
const moon = cardById('major-18-moon')!;
const swords3 = cardById('swords-03-three')!;
const lovers = cardById('major-06-lovers')!;
const fool = cardById('major-00-fool')!;

describe('the card template (spec stage 6 §4, rules §12)', () => {
  it('writes the facts line, linking the suit of a minor card to its block on the hub', () => {
    expect(factsLine(cardPage(moon, 'en'), EN, 'en')).toEqual({ before: 'Major Arcana · card XVIII', link: null, after: '' });
    expect(factsLine(cardPage(swords3, 'en'), EN, 'en')).toEqual({ before: 'Minor Arcana · ',
      link: { text: 'Swords', href: '/cards#swords' }, after: ' · Three' });
    expect(factsLine(cardPage(swords3, 'es'), ES, 'es')).toEqual({ before: 'Arcanos menores · ',
      link: { text: 'Espadas', href: '/es/cartas#espadas' }, after: ' · Tres' });
    expect(factsLine(cardPage(lovers, 'es'), ES, 'es').after).toBe(' · Los Amantes'); // facts.also_called
  });

  it('captions the scan and the keyword table and pairs the keyword columns', () => {
    expect(imageCaption(cardPage(moon, 'en'), EN)).toBe('The Moon, 1909 Rider–Waite–Smith deck ("Roses & Lilies" '
      + 'printing), drawn by Pamela Colman Smith. Public-domain scan, Wikimedia Commons.');
    expect(keywordCaption(cardPage(moon, 'es'), ES)).toBe('La Luna: palabras clave');
    expect(keywordRows(cardPage(moon, 'en'))).toEqual([['uncertainty', 'confusion lifting'], ['intuition', 'worry'],
      ['dreams', 'clearer sight'], ['hidden feelings', '']]);
  });

  it('cites Waite with the page list of the edition', () => {
    expect(formatPages([286], EN)).toBe('p. 286');
    expect(formatPages([140, 143], ES)).toBe('pp. 140, 143');
    expect(waiteCite(cardPage(moon, 'en'), EN)).toBe('A. E. Waite, The Pictorial Key to the Tarot (1911), p. 286');
  });

  it('builds the yes/no lines from the deck verdict and the reason of the card base', () => {
    expect(yesNoLines(moon, yesNoReason(moon, 'en'), EN, 'en')).toEqual({
      upright: "Upright: Not clear yet. Under the Moon's light the path is only half visible, and shapes are hard to read.",
      reversed: 'Reversed: Not clear yet.', rule: EN.yes_no.rule });
    expect(yesNoLines(swords3, yesNoReason(swords3, 'en'), EN, 'en').upright)
      .toBe('Upright: No. Three swords pierce the heart under a rainy sky, a picture of hurt rather than ease.');
    expect(yesNoLines(moon, yesNoReason(moon, 'es'), ES, 'es').reversed).toBe('Al revés: Todavía no está claro.');
  });

  it('names both cards of a pair and links the other one', () => {
    expect(pairRows(cardPage(moon, 'en'), EN, 'en')[0]).toEqual({ before: 'The Moon + ',
      link: { text: 'The Sun', href: '/cards/the-sun' }, after: '',
      reading: 'Uncertainty giving way to clarity. Wait for daylight before you decide.' });
    expect(pairRows(cardPage(moon, 'es'), ES, 'es')[0].link).toEqual({ text: 'El Sol', href: '/es/cartas/el-sol' });
  });

  it('links the first mention of another card, in the blocks or in the FAQ answers', () => {
    const segments = mentionSegments(cardPage(moon, 'en'), 'en').get('not_to_confuse:0')!;
    expect(segments[1]).toEqual({ text: 'High Priestess', href: '/cards/the-high-priestess' });
    expect((segments[0] as string).endsWith("In Waite's description of the ")).toBe(true);
    const foolFaq = mentionSegments(cardPage(fool, 'en'), 'en').get('faq:3')!;
    expect(foolFaq).toContainEqual({ text: 'The Magician', href: '/cards/the-magician' });
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
    expect(ctaText(cardPage(swords3, 'en'), EN).heading).toBe('Draw the Three of Swords for your question');
    expect(ctaText(cardPage(moon, 'es'), ES).heading).toBe('¿Qué dice La Luna de tu pregunta?');
    expect(faqHeading(cardPage(moon, 'en'), EN)).toBe('Questions about The Moon');
  });

  it('signs the page with the editor and the date of the review', () => {
    expect(formatDate('2026-11-23', 'en')).toBe('November 23, 2026');
    expect(formatDate('2026-11-23', 'es')).toBe('23 de noviembre de 2026');
    const about = aboutLines(cardPage(moon, 'en'), EN, 'en', 'Adrian Solenne');
    expect(about.method).toBe("Written with AI from Waite's book and Arcana Diary's card meanings. Reviewed by "
      + 'Adrian Solenne on November 23, 2026.');
    expect(about.sources[1]).toEqual({ what: 'Description of the picture, traditional meanings and quotes',
      where: 'A. E. Waite, The Pictorial Key to the Tarot (1911)', pages: 'pp. 27, 76, 140, 143, 286',
      url: 'https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot' });
    expect(about.sources[2].url).toBeNull();
  });

  it('gives the sections the anchors of the page maps (EN #reversed; ES #invertida, #amor, #si-o-no)', () => {
    expect([SECTION_IDS.en.reversed, SECTION_IDS.en.love]).toEqual(['reversed', 'love']);
    expect([SECTION_IDS.es.reversed, SECTION_IDS.es.love, SECTION_IDS.es.yes_no]).toEqual(['invertida', 'amor', 'si-o-no']);
    expect(tocLinks('es')).toEqual([{ href: '#al-derecho', label: 'Al derecho' }, { href: '#invertida', label: 'Al revés' },
      { href: '#amor', label: 'Amor' }, { href: '#trabajo-y-dinero', label: 'Trabajo y dinero' },
      { href: '#si-o-no', label: 'Sí o no' }, { href: '#preguntas', label: 'Preguntas' }]);
  });
});
