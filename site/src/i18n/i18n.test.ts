import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { DICTS, DRAFTS, fill, placeholders, t } from './index';

const keys = (lang: 'en' | 'es') => Object.keys(DICTS[lang]).sort();

describe('dictionaries', () => {
  it('keep the stage 6 menu and breadcrumb words (stage 2 menu table, prototypes)', () => {
    expect([t('en').navCards, t('es').navCards]).toEqual(['Card Meanings', 'Significados']);
    expect([t('en').crumbHome, t('es').crumbHome, t('en').crumbCards, t('es').crumbCards]).toEqual(['Home', 'Inicio',
      'Cards', 'Cartas']);
    expect([t('en').crumbMajor, t('es').crumbMajor]).toEqual(['Major Arcana', 'Arcanos mayores']);
    expect([t('en').breadcrumbLabel, t('es').breadcrumbLabel]).toEqual(['Breadcrumb', 'Ruta']);
  });

  it('use the anchors of the stage 2 link matrix (docs/research/stage2/links-{en,es}.csv)', () => {
    expect([t('en').fmtLove, t('en').fmtCards, t('en').yesNoMethodLink]).toEqual([
      'Love reading', 'Card meanings', 'How we read yes and no']);
    expect([t('es').fmtThree, t('es').fmtCards, t('es').cardLoveLink, t('es').cardYesNoLink]).toEqual([
      'Tirada de 3 cartas', 'Significados de las cartas', 'Haz una tirada de amor', 'Pregunta sí o no']);
    expect([t('en').drawForQuestion, t('es').drawForQuestion, t('en').allCardsLink, t('es').allCardsLink,
      t('en').yesNoListAsk]).toEqual(['Draw a card for your question', 'Saca una carta para tu pregunta', 'All 78 cards',
      'Las 78 cartas', 'Ask your question']);
    // L-EN-26 (love block of the card page) and the hints of the hub link (context terms of L-EN-21 / L-ES-21)
    expect([t('en').cardLoveLink, t('en').fmtCardsHint, t('es').fmtCardsHint]).toEqual([
      'Do a love reading', 'What each of the 78 tarot cards means', 'Qué significa cada una de las 78 cartas del tarot']);
    // under a drawn card (owner decisions 38, 41): L-EN-01…03/31, L-ES-01/02; L-EN-15, L-ES-15; L-ES-03; L-ES-04
    // (a card that says "not clear yet": the short question); L-ES-23 after L-ES-03 in the same row
    expect([t('en').fullMeaning, t('es').fullMeaning, t('en').dailyCardLink, t('es').dailyCardLink, t('es').drawnLoveLink,
      t('es').drawnWhyLink, t('es').drawnWhyUnclearLink, t('es').drawnFullShort]).toEqual(['{name} — full meaning',
      '{name} — significado completo', "Today's card: {name}", 'Carta de hoy: {name}', '{name} en el amor',
      'Por qué {name} dice {verdict}', '¿Por qué {name}?', 'significado completo']);
  });

  it('use the exact words of the stage 8.1 spec (2026-11-27 §2.1, §2.3)', () => {
    expect([t('en').dailyStreak, t('en').dailyCalendarLink, t('es').dailyStreak, t('es').dailyCalendarLink]).toEqual([
      'Day {n} in a row', 'Your month in cards', 'Día {n} seguido', 'Tu mes en cartas']);
    expect([t('en').eveningQuestion, t('es').eveningQuestion]).toEqual([
      "Did today's card show up in your day?", '¿Apareció la carta de hoy en tu día?']);
    expect([t('en').feltYes, t('en').feltPartly, t('en').feltNo, t('es').feltYes, t('es').feltPartly, t('es').feltNo])
      .toEqual(['Yes', 'Partly', 'No', 'Sí', 'En parte', 'No']);
    expect([t('en').navDaily, t('es').navDaily, t('en').calendarSignIn]).toEqual([
      'Card of the Day', 'Carta del día', 'Sign in to keep your cards']);
  });

  it('have the same keys in English and Spanish', () => {
    expect(keys('es')).toEqual(keys('en'));
    expect(keys('en').length).toBe(289);
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
    // stage 5: every key is reviewed
    expect(DRAFTS.en).toEqual([]);
    expect(DRAFTS.es).toEqual([]);
  });

  it('keep the prototype copy', () => {
    expect(t('en').homeH1).toBe('Free tarot reading: ask the cards');
    expect(t('en').drawThree).toBe('Draw three cards');
    expect(t('es').drawThree).toBe('Saca tres cartas');
    expect(t('es').homeH1).toBe('Tarot gratis: pregunta a las cartas');
    expect(t('en').disclaimer).toBe('Tarot is a way to think about your question, not a guarantee.');
    expect(t('es').disclaimer).toBe('El tarot es una forma de reflexionar, no una garantía.');
    expect(t('es').whyPrefix).toBe('Por qué:');
    // spec 4.5 §4: the yes/no toggle of prototype 5a
    expect(t('en').yesNoCountHint).toBe('1 card — a quick lean. 3 cards — the majority decides, and you see what tips it.');
    expect([t('en').oneCardChip, t('en').threeCardsChip, t('en').countGroupLabel]).toEqual(['1 card', '3 cards', 'Number of cards']);
    expect([t('es').oneCardChip, t('es').threeCardsChip]).toEqual(['1 carta', '3 cartas']);
  });

  it('keep the 4.4b copy of the prototypes and the spec (spec 4.4b §8)', () => {
    expect([t('en').freeSaveAfter, t('es').freeSaveAfter]).toEqual(['Free · save it to your diary after',
      'Gratis · guárdala en tu diario después']);
    expect(t('en').howStep3).toBe('Save it, and check later what came true.');
    expect([t('en').navDiary, t('es').navDiary, t('en').navDiaryShort, t('es').navDiaryShort]).toEqual([
      'Your diary', 'Tu diario', 'Diary', 'Diario']);
    expect([t('en').plusBenefit3, t('es').plusBenefit3]).toEqual(['Your whole diary, with no limit', 'Todo tu diario, sin límite']);
    expect([t('en').plusDiaryNote, t('es').plusDiaryNote]).toEqual(['Your diary shows your last 10 readings. Plus shows all of them.',
      'Tu diario muestra tus últimas 10 lecturas. Plus las muestra todas.']);
    expect([t('en').saveToDiary, t('es').saveToDiary, t('en').savedToDiary]).toEqual(['Save to diary', 'Guardar en el diario',
      'Saved to your diary ✓']);
  });

  it('say that a sign-in switched the reminder on (owner decision 16)', () => {
    expect([fill(t('en').diaryReminderOn, { account: t('en').diaryReminderOnLink }),
      fill(t('es').diaryReminderOn, { account: t('es').diaryReminderOnLink })]).toEqual([
      'The reminder in 7 days is on — you can turn it off in your account.',
      'El recordatorio en 7 días está activado; puedes desactivarlo en tu cuenta.']);
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

  it('keep the stage 4.9 copy: the third position, the love caption, the sign-in line (spec 4.9 §1)', () => {
    expect([t('en').posPath, t('es').posPath]).toEqual(["Where it's heading", 'Hacia dónde va']);
    expect(t('en').loveLead).toBe("Three cards about you and your relationship: the past, the present and where it's heading.");
    expect(t('es').loveLead).toBe('Tres cartas sobre ti y tu relación: el pasado, el presente y hacia dónde va.');
    expect([t('en').diarySignInSoon, t('es').diarySignInSoon]).toEqual([
      "Signing in isn't available right now.", 'El acceso no está disponible en este momento.']);
  });

  it.runIf(existsSync('../api/app/safety'))('carry the AI provider line word for word from the API safety texts', () => {
    for (const lang of ['en', 'es'] as const) {
      const api = JSON.parse(readFileSync(`../api/app/safety/texts.${lang}.json`, 'utf8'));
      expect(t(lang).providerLine).toBe(api.provider_disclosure);
    }
  });
});
