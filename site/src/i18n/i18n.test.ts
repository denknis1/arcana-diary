import { describe, expect, it } from 'vitest';
import { DICTS, DRAFTS, fill, placeholders, t } from './index';

const keys = (lang: 'en' | 'es') => Object.keys(DICTS[lang]).sort();

describe('dictionaries', () => {
  it('have the same keys in English and Spanish', () => {
    expect(keys('es')).toEqual(keys('en'));
    expect(keys('en').length).toBe(222);
  });

  it('have no empty strings', () => {
    for (const lang of ['en', 'es'] as const) {
      for (const [key, value] of Object.entries(DICTS[lang])) expect(value.trim(), `${lang}.${key}`).not.toBe('');
    }
  });

  it('use the same placeholders in both languages', () => {
    for (const key of keys('en')) {
      const k = key as keyof typeof DICTS.en;
      expect(placeholders(DICTS.es[k]), key).toEqual(placeholders(DICTS.en[k]));
    }
  });

  it('mark drafts only with real keys, each once', () => {
    for (const lang of ['en', 'es'] as const) {
      expect(new Set(DRAFTS[lang]).size).toBe(DRAFTS[lang].length);
      for (const key of DRAFTS[lang]) expect(keys(lang)).toContain(key);
    }
    expect(DRAFTS.en.length).toBe(105);
    expect(DRAFTS.es.length).toBe(176);
  });

  it('keep the prototype copy', () => {
    expect(t('en').homeH1).toBe('Ask the cards.');
    expect(t('en').drawThree).toBe('Draw three cards');
    expect(t('es').drawThree).toBe('Saca tres cartas');
    expect(t('es').homeH1).toBe('Pregunta a las cartas.');
    expect(t('en').disclaimer).toBe('Tarot is a way to think about your question, not a guarantee.');
    expect(t('es').disclaimer).toBe('El tarot es una forma de reflexionar, no una garantía.');
    expect(t('es').whyPrefix).toBe('Por qué:');
    // spec 4.5 §4: the yes/no toggle of prototype 5a; the Spanish hint is a draft
    expect(t('en').yesNoCountHint).toBe('1 card — a quick lean. 3 cards — the majority decides, and you see what tips it.');
    expect([t('en').oneCardChip, t('en').threeCardsChip, t('en').countGroupLabel]).toEqual(['1 card', '3 cards', 'Number of cards']);
    expect([t('es').oneCardChip, t('es').threeCardsChip]).toEqual(['1 carta', '3 cartas']);
    expect(DRAFTS.es).toContain('yesNoCountHint');
    expect(DRAFTS.en).not.toContain('yesNoCountHint');
  });

  it('name the votes with the card base labels (content/cards/yes-no-rules.json)', () => {
    expect([t('en').voteYes, t('en').voteNo, t('en').voteUnclear]).toEqual(['Yes', 'No', 'Not clear yet']);
    expect([t('es').voteYes, t('es').voteNo, t('es').voteUnclear]).toEqual(['Sí', 'No', 'Todavía no está claro']);
  });

  it('name a reversed card so the word agrees with every card name (stage 4.6, owner decision 3)', () => {
    expect(t('en').reversedTag).toBe('Reversed');
    expect(t('es').reversedTag).toBe('Al revés');
    expect([t('es').cardAlt, t('es').cardAltReversed, t('es').reversedTitle]).toEqual([
      '{name}, al derecho', '{name}, carta invertida', '{name}, carta invertida',
    ]);
    // "El Emperador, invertida" / "El As de Copas, derecha" clash with masculine names: only "carta invertida" agrees
    for (const [key, value] of Object.entries(DICTS.es)) {
      expect(value.replace(/carta invertida/gi, ''), key).not.toMatch(/invertid|\bderecha\b/i);
    }
  });

  it('never call a reading a forecast (design decision 13.11.2026)', () => {
    for (const lang of ['en', 'es'] as const) {
      for (const value of Object.values(DICTS[lang])) expect(value.toLowerCase()).not.toMatch(/forecast|pronóstico|predic/);
    }
  });
});

describe('fill', () => {
  it('puts values into placeholders and leaves unknown ones', () => {
    expect(fill('{name} — full meaning', { name: 'The Moon' })).toBe('The Moon — full meaning');
    expect(fill('{n} left of {m}', { n: 2 })).toBe('2 left of {m}');
    expect(placeholders('{a} {b} {a}')).toEqual(['a', 'b']);
  });
});
