import { describe, expect, it } from 'vitest';
import { DICTS, DRAFTS, fill, placeholders, t } from './index';

const keys = (lang: 'en' | 'es') => Object.keys(DICTS[lang]).sort();

describe('dictionaries', () => {
  it('have the same keys in English and Spanish', () => {
    expect(keys('es')).toEqual(keys('en'));
    expect(keys('en').length).toBe(156);
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
    expect(DRAFTS.en.length).toBe(57);
    expect(DRAFTS.es.length).toBe(115);
  });

  it('keep the prototype copy', () => {
    expect(t('en').homeH1).toBe('Ask the cards.');
    expect(t('en').drawThree).toBe('Draw three cards');
    expect(t('es').drawThree).toBe('Saca tres cartas');
    expect(t('es').homeH1).toBe('Pregunta a las cartas.');
    expect(t('en').disclaimer).toBe('Tarot is a way to think about your question, not a guarantee.');
    expect(t('es').disclaimer).toBe('El tarot es una forma de reflexionar, no una garantía.');
    expect(t('es').whyPrefix).toBe('Por qué:');
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
