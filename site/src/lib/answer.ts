// The reader's answer by sections (spec 4.2 §2.2): built from `text` events while it streams, replaced whole by
// `replace` / `fallback`, laid out in a fixed order for the screen. Texts are shown with textContent only.
import type { SseEvent } from './sse';
import type { DrawnCard, ReadingView } from './types';

export const SECTION_ORDER = ['headline', 'card1', 'card2', 'card3', 'synthesis', 'step', 'why'] as const;
export type SectionName = (typeof SECTION_ORDER)[number];
export type Sections = Partial<Record<SectionName, string>>;

export interface Answer {
  sections: Sections;
  started: boolean; // some text has arrived
  shown: 'model' | 'fallback' | null; // from `done` (or the restored reading)
  replaced: 'replace' | 'fallback' | null; // the last whole-answer replacement, if any
  retry: boolean; // a fallback answer that POST /retry may still replace
}

export const EMPTY_ANSWER: Answer = { sections: {}, started: false, shown: null, replaced: null, retry: false };

function isSection(name: unknown): name is SectionName {
  return typeof name === 'string' && (SECTION_ORDER as readonly string[]).includes(name);
}

export function pickSections(raw: unknown): Sections {
  const out: Sections = {};
  if (raw && typeof raw === 'object') {
    for (const [name, text] of Object.entries(raw)) if (isSection(name) && typeof text === 'string') out[name] = text;
  }
  return out;
}

export function applyAnswerEvent(answer: Answer, event: SseEvent): Answer {
  const data = (event.data && typeof event.data === 'object' ? event.data : {}) as Record<string, unknown>;
  switch (event.event) {
    case 'text': {
      if (!isSection(data.name) || typeof data.text !== 'string') return answer;
      const name = data.name;
      return { ...answer, started: true, sections: { ...answer.sections, [name]: (answer.sections[name] ?? '') + data.text } };
    }
    case 'replace':
    case 'fallback':
      return {
        ...answer,
        started: true,
        sections: pickSections(data.sections),
        replaced: event.event,
        retry: event.event === 'fallback' && data.retry === true,
      };
    case 'done':
      if (data.answer_shown === 'model' || data.answer_shown === 'fallback') return { ...answer, shown: data.answer_shown };
      return answer;
    default:
      return answer;
  }
}

/** The answer of GET /api/readings/{id} (after a broken stream). */
export function answerFromView(view: ReadingView): Answer {
  const shown = view.answer_shown === 'model' || view.answer_shown === 'fallback' ? view.answer_shown : null;
  return {
    sections: pickSections(view.answer),
    started: view.answer !== null,
    shown,
    replaced: shown === 'fallback' ? 'fallback' : null,
    retry: shown === 'fallback' && view.retries_left > 0,
  };
}

export type AnswerBlock =
  | { kind: 'headline' | 'synthesis' | 'step' | 'why'; text: string }
  | { kind: 'card'; text: string; card: DrawnCard };

/** What the screen shows, in order: headline, a block per drawn card, synthesis, one step, why. */
export function answerBlocks(answer: Answer, cards: readonly DrawnCard[]): AnswerBlock[] {
  const blocks: AnswerBlock[] = [];
  for (const name of SECTION_ORDER) {
    const text = answer.sections[name]?.trim();
    if (!text) continue;
    if (name === 'card1' || name === 'card2' || name === 'card3') {
      const card = cards[Number(name.slice(4)) - 1];
      if (card) blocks.push({ kind: 'card', text, card });
    } else {
      blocks.push({ kind: name, text });
    }
  }
  return blocks;
}
