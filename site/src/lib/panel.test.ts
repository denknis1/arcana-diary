import { describe, expect, it } from 'vitest';
import { t } from '../i18n';
import { buildCreateBody, QUESTION_MAX, cleanQuestion, cardsFor, drawLabelKey, initialKind, panelConfig, situationKey, toolFor } from './panel';
import { SITUATIONS } from './types';

describe('panelConfig', () => {
  it('draws three cards on the home pages, with the 1 / 3 toggle only in Spanish', () => {
    expect(panelConfig('home', 'en')).toMatchObject({ tool: 'home', kind: 'three', countToggle: false });
    expect(panelConfig('home', 'es')).toMatchObject({ tool: 'home', kind: 'three', countToggle: true });
  });

  it('sets up one card, yes/no, love and the card page', () => {
    expect(panelConfig('one_card', 'en')).toMatchObject({ tool: 'one_card', kind: 'one' });
    expect(panelConfig('yes_no', 'es')).toMatchObject({ tool: 'yes_no', kind: 'yes_no', labelKey: 'yesNoLabel' });
    expect(panelConfig('love', 'en')).toMatchObject({ tool: 'love', kind: 'three', topic: 'love', situations: true });
    expect(panelConfig('card', 'en', 'major-18-moon')).toMatchObject({
      tool: 'one_card', entry: 'card_page', kind: 'card_page', cardId: 'major-18-moon',
    });
  });

  it('counts one card on the Spanish home as the one-card tool', () => {
    expect(toolFor(panelConfig('home', 'es'), 'one')).toBe('one_card');
    expect(toolFor(panelConfig('home', 'es'), 'three')).toBe('home');
    expect(toolFor(panelConfig('card', 'en', 'x'), 'card_page')).toBe('one_card');
    expect(toolFor(panelConfig('yes_no', 'en'), 'yes_no')).toBe('yes_no');
  });

  it('starts the Spanish home with one card at #una-carta', () => {
    expect(initialKind(panelConfig('home', 'es'), '#una-carta')).toBe('one');
    expect(initialKind(panelConfig('home', 'es'), '')).toBe('three');
    expect(initialKind(panelConfig('home', 'en'), '#una-carta')).toBe('three');
  });
});

describe('draw button', () => {
  it('says what happens', () => {
    expect(t('en')[drawLabelKey(panelConfig('home', 'en'), 'three')]).toBe('Draw three cards');
    expect(t('es')[drawLabelKey(panelConfig('home', 'es'), 'one')]).toBe('Saca una carta');
    expect(t('en')[drawLabelKey(panelConfig('yes_no', 'en'), 'yes_no')]).toBe('Draw a card');
    expect(t('en')[drawLabelKey(panelConfig('love', 'en'), 'three')]).toBe('Draw for love');
    expect(t('es')[drawLabelKey(panelConfig('card', 'es', 'x'), 'card_page')]).toBe('Saca una carta para tu pregunta');
    expect(cardsFor('three')).toBe(3);
    expect(cardsFor('yes_no')).toBe(1);
  });
});

describe('buildCreateBody', () => {
  it('sends only what was given, the question trimmed and cut to 500', () => {
    expect(buildCreateBody(panelConfig('home', 'en'), { kind: 'three', question: '   ', situation: null, tz: undefined }))
      .toEqual({ lang: 'en', kind: 'three' });
    const long = 'a'.repeat(600);
    expect(buildCreateBody(panelConfig('one_card', 'es'), { kind: 'one', question: ` ${long} `, situation: null, tz: 'America/Bogota' }))
      .toEqual({ lang: 'es', kind: 'one', question: 'a'.repeat(500), tz: 'America/Bogota' });
  });

  it('adds the love topic and situation, and the card of a card page', () => {
    expect(buildCreateBody(panelConfig('love', 'en'), { kind: 'three', question: 'Closer?', situation: 'after_breakup', tz: 'UTC' }))
      .toEqual({ lang: 'en', kind: 'three', question: 'Closer?', topic: 'love', situation: 'after_breakup', tz: 'UTC' });
    expect(buildCreateBody(panelConfig('love', 'en'), { kind: 'three', question: '', situation: null, tz: undefined }))
      .toEqual({ lang: 'en', kind: 'three', topic: 'love' });
    expect(buildCreateBody(panelConfig('card', 'en', 'major-18-moon'), { kind: 'card_page', question: '', situation: null, tz: undefined }))
      .toEqual({ lang: 'en', kind: 'card_page', card_id: 'major-18-moon' });
  });

  it('names the four love situations of stage 3', () => {
    expect(SITUATIONS.map((s) => t('en')[situationKey(s)])).toEqual(['Single', 'In a relationship', 'After a breakup', "It's complicated"]);
  });
});

describe('cleanQuestion', () => {
  it('cuts by code points, never splitting an emoji', () => {
    const q = 'a'.repeat(QUESTION_MAX - 1) + '😀' + 'tail';
    const out = cleanQuestion(q);
    expect(Array.from(out)).toHaveLength(QUESTION_MAX);
    expect(out.endsWith('😀')).toBe(true);
  });
});
