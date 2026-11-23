import { describe, expect, it } from 'vitest';
import { FACTS, fillFacts, missingFacts } from './facts';

describe('facts (spec stage 6 §2, owner decision 36)', () => {
  it('hold the limits, the yes/no counts and the editor, nothing about the operator yet', () => {
    expect(Object.keys(FACTS).sort()).toEqual(['diary_free', 'editor_name', 'followups', 'guest_limit', 'no_count',
      'unclear_count', 'user_limit', 'yes_count']);
    expect(Number(FACTS.yes_count) + Number(FACTS.no_count) + Number(FACTS.unclear_count)).toBe(78);
    expect(FACTS.editor_name).toBe('Adrian Solenne');
  });

  it('fill the placeholders they know and leave the others', () => {
    expect(fillFacts('{guest_limit} a day, {operator_name}', { guest_limit: 2 })).toBe('2 a day, {operator_name}');
    expect(fillFacts(`{user_limit}`)).toBe(String(FACTS.user_limit));
  });

  it('list the placeholders without a value, once each, sorted', () => {
    expect(missingFacts(['{b} {guest_limit}', '{a} {b}'], { guest_limit: 2 })).toEqual(['a', 'b']);
    expect(missingFacts(['no placeholder'])).toEqual([]);
  });
});
