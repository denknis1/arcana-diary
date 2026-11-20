import { describe, expect, it } from 'vitest';
import { EMPTY_ANSWER, answerBlocks, answerFromView, applyAnswerEvent, type Answer } from './answer';
import type { SseEvent } from './sse';
import type { DrawnCard, ReadingView } from './types';

const CARDS: DrawnCard[] = [
  { card_id: 'major-16-tower', position: 'past', reversed: false, name: 'The Tower' },
  { card_id: 'major-18-moon', position: 'present', reversed: true, name: 'The Moon' },
  { card_id: 'major-19-sun', position: 'path', reversed: false, name: 'The Sun' },
];

const run = (events: SseEvent[], start: Answer = EMPTY_ANSWER) => events.reduce(applyAnswerEvent, start);
const text = (name: string, t: string): SseEvent => ({ event: 'text', data: { name, text: t } });

describe('applyAnswerEvent', () => {
  it('builds sections from streamed pieces', () => {
    const answer = run([
      { event: 'section', data: { name: 'headline' } },
      text('headline', 'A change '), text('headline', 'you did not choose.'),
      text('card1', 'The Tower may point to a sudden change.'),
      { event: 'done', data: { answer_shown: 'model' } },
    ]);
    expect(answer.sections).toEqual({ headline: 'A change you did not choose.', card1: 'The Tower may point to a sudden change.' });
    expect(answer).toMatchObject({ started: true, shown: 'model', replaced: null, retry: false });
  });

  it('replaces the whole answer on replace and fallback, keeping the retry flag', () => {
    const replaced = run([text('headline', 'Bad'), { event: 'replace', data: { sections: { headline: 'Good', step: 'Breathe.' }, reason: 'why' } }]);
    expect(replaced.sections).toEqual({ headline: 'Good', step: 'Breathe.' });
    expect(replaced.replaced).toBe('replace');
    const fallback = run([{ event: 'fallback', data: { sections: { headline: 'The reader is unavailable…' }, reason: 'timeout', retry: true } }]);
    expect(fallback).toMatchObject({ replaced: 'fallback', retry: true, started: true });
  });

  it('ignores unknown sections, foreign events and the crisis marker', () => {
    const answer = run([text('crisis', 'x'), text('followup', 'y'), { event: 'meta', data: {} }, { event: 'ping', data: 'z' }]);
    expect(answer).toEqual(EMPTY_ANSWER);
  });
});

describe('answerBlocks', () => {
  it('orders blocks and ties each card section to its card', () => {
    const answer = run([text('step', ' Talk to someone. '), text('card2', 'Moon text'), text('headline', 'Head'),
      text('synthesis', 'Together'), text('card1', 'Tower text')]);
    expect(answerBlocks(answer, CARDS)).toEqual([
      { kind: 'headline', text: 'Head' },
      { kind: 'card', text: 'Tower text', card: CARDS[0] },
      { kind: 'card', text: 'Moon text', card: CARDS[1] },
      { kind: 'synthesis', text: 'Together' },
      { kind: 'step', text: 'Talk to someone.' },
    ]);
  });

  it('drops empty sections and card sections without a card', () => {
    const answer = run([text('headline', '   '), text('card3', 'Third'), text('why', 'Because')]);
    expect(answerBlocks(answer, CARDS.slice(0, 1))).toEqual([{ kind: 'why', text: 'Because' }]);
  });
});

describe('answerFromView', () => {
  it('restores the saved answer of GET /api/readings/{id}', () => {
    const view = { answer: { headline: 'H', card1: 'C', extra: 'x' }, answer_shown: 'fallback', retries_left: 1 } as unknown as ReadingView;
    expect(answerFromView(view)).toEqual({ sections: { headline: 'H', card1: 'C' }, started: true, shown: 'fallback', replaced: 'fallback', retry: true });
  });
});
