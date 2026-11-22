// The night room with a whole answer on screen, for screen tests (NightRoom.test.tsx, useSaveToDiary.test.tsx).
import { CLOSED, nightReducer, type NightAction, type NightState } from '../nightRoom';
import type { ReadingCreated } from '../types';

export const ONE: ReadingCreated = {
  id: 'r1', lang: 'en', kind: 'one', verdict: null, soft_line: null, remaining: 1,
  cards: [{ card_id: 'major-18-moon', position: 'card', reversed: false, name: 'The Moon' }],
};

/** The room with the whole answer shown (cards turned, stream done). */
export function shown(reading: ReadingCreated, sections: Record<string, string>): NightState {
  const actions: NightAction[] = [
    { type: 'open' }, { type: 'created', reading, reducedMotion: true },
    { type: 'stream', event: { event: 'meta', data: { soft_line: null } } },
    ...Object.entries(sections).flatMap(([name, text]): NightAction[] => [
      { type: 'stream', event: { event: 'section', data: { name } } },
      { type: 'stream', event: { event: 'text', data: { name, text } } },
    ]),
    { type: 'stream', event: { event: 'done', data: { answer_shown: 'model' } } },
    { type: 'counts', counts: { followups_left: 2, followup_attempts_left: 8 } },
  ];
  return actions.reduce(nightReducer, CLOSED);
}
