// Shapes shared by the site's modules: page language, tools, and what the API (api/README.md) sends back.

export type Lang = 'en' | 'es';
export const LANGS: readonly Lang[] = ['en', 'es'];

/** The `tool` of docs/design/analytics-events.md that the pages use (three_cards: /es/tiradas/3-cartas, stage 6). */
export type Tool = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily' | 'three_cards';

/** `kind` of POST /api/readings. */
export type Kind = 'one' | 'three' | 'yes_no' | 'card_page';

export type Position = 'past' | 'present' | 'path' | 'card';

/** A yes/no answer: the reading's verdict, or one card's own vote (spec 4.5 §4). */
export type Vote = 'yes' | 'no' | 'unclear';

/** How many cards a yes/no reading draws (spec 4.5 §4); one is the default. */
export type CardCount = 1 | 3;

export type Situation = 'single' | 'relationship' | 'after_breakup' | 'complicated';
export const SITUATIONS: readonly Situation[] = ['single', 'relationship', 'after_breakup', 'complicated'];

export interface DrawnCard {
  card_id: string;
  position: Position;
  reversed: boolean;
  name: string;
  vote?: Vote; // a yes/no reading with a verdict: this card's own vote (spec 4.5 §4)
}

export interface Verdict {
  value: Vote;
  label: string;
}

/** 201 of POST /api/readings. */
export interface ReadingCreated {
  id: string;
  lang: Lang;
  kind: Kind;
  cards: DrawnCard[];
  verdict: Verdict | null;
  soft_line: string | null;
  remaining: number;
}

export interface HelpLine {
  name: string;
  number?: string;
  sms?: string;
  url?: string;
  note?: string;
  channels: string[];
  hours: string | null;
  topic: string;
  purpose: string;
}

/** 200 {"group": "crisis", ...} of POST /api/readings and of a follow-up, and the `crisis` stream event. */
export interface CrisisPayload {
  group: 'crisis';
  crisis: {
    title: string;
    body: string;
    not_saved: string;
    contacts_intro: string;
    emergency_line: string;
    fallback_contacts: string;
    closing: string;
  };
  helplines: { country: string | null; source: string; lines: HelpLine[] };
}

export interface FollowupCounts {
  followups_left: number;
  followup_attempts_left: number;
}

/** GET /api/readings/{id} for its owner (the fields 4.4a uses). */
export interface ReadingView extends FollowupCounts {
  id: string;
  kind: Kind;
  cards: DrawnCard[];
  verdict: Verdict | null;
  soft_line: string | null;
  answer: Record<string, string> | null;
  answer_shown: 'model' | 'fallback' | 'crisis' | null;
  status: 'pending' | 'streaming' | 'done';
  retries_left: number;
  followups: SavedFollowup[];
}

/** A follow-up with its answer as GET /api/readings/{id} keeps it (answered ones only). */
export interface SavedFollowup {
  n: number;
  question: string;
  answer: string | null;
  soft_line: string | null;
}

/** 200 of GET /api/daily. */
export interface DailyCard {
  day: string;
  card: { card_id: string; name: string; reversed: boolean };
  text: string;
  source: 'cache' | 'fallback';
}

/** Body of POST /api/readings. */
export interface CreateBody {
  lang: Lang;
  kind: Kind;
  question?: string;
  topic?: 'love';
  situation?: Situation;
  card_id?: string;
  tz?: string;
  turnstile_token?: string;
  count?: CardCount; // yes/no only
  request_id?: string; // spec 4.5 §5: one number per press of Draw, the same on its one automatic repeat
}
