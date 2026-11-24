import { describe, expect, it } from 'vitest';
import { FACTS, fillFacts, missingFacts } from './facts';

describe('facts (spec stage 6 §2, owner decision 36)', () => {
  it('hold the limits, the yes/no counts, the editor and the operator facts that are filled in', () => {
    // content/operator.json: name, address and jurisdiction are still empty, so they are not here
    expect(Object.keys(FACTS).sort()).toEqual(['contact_email', 'diary_free', 'editor_name', 'effective_date',
      'email_provider', 'followups', 'guest_limit', 'hosting_provider', 'no_count', 'unclear_count', 'user_limit',
      'yes_count']);
    expect(Number(FACTS.yes_count) + Number(FACTS.no_count) + Number(FACTS.unclear_count)).toBe(78);
    expect(FACTS.editor_name).toBe('Adrian Solenne');
  });

  it('fill the placeholders they know and leave the others', () => {
    expect(fillFacts('{guest_limit} a day, {operator_name}', { guest_limit: 2 })).toBe('2 a day, {operator_name}');
    expect(fillFacts(`{user_limit}`)).toBe(String(FACTS.user_limit));
  });

  it('write a date in the language of the page', () => {
    const facts = { effective_date: { en: 'December 14, 2026', es: '14 de diciembre de 2026' } };
    expect(fillFacts('From {effective_date}.', facts, 'en')).toBe('From December 14, 2026.');
    expect(fillFacts('Desde {effective_date}.', facts, 'es')).toBe('Desde 14 de diciembre de 2026.');
    expect(fillFacts('From {effective_date}.', facts)).toBe('From {effective_date}.'); // no language: not filled
  });

  it('list the placeholders without a value, once each, sorted', () => {
    expect(missingFacts(['{b} {guest_limit}', '{a} {b}'], { guest_limit: 2 })).toEqual(['a', 'b']);
    expect(missingFacts(['no placeholder'])).toEqual([]);
  });
});
