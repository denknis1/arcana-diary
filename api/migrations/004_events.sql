-- 004_events: stage 4.4a (spec 2026-11-19 §6): our own event counter for the funnel of
-- docs/design/analytics-events.md. No address, cookie, account or device id is stored: a row is the event name,
-- the tool, the page language, the whitelisted parameters, the UTC day and the time. As for the other tables:
-- row level security on, no policies, no rights for the browser roles (migrate() revokes them). The id is a
-- random row key, not a person, and needs no sequence.
CREATE TABLE events (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    day        date NOT NULL,
    name       text NOT NULL CHECK (name IN ('tool_view', 'draw_click', 'night_open', 'cards_revealed',
                                             'reading_shown', 'save_click', 'signup_done', 'more_about_cards',
                                             'outcome_answered', 'plus_view')),
    tool       text CHECK (tool IN ('home', 'one_card', 'yes_no', 'love', 'daily', 'three_cards')),
    lang       text NOT NULL CHECK (lang IN ('en', 'es')),
    params     jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL
);
CREATE INDEX events_day_name_idx ON events (day, name);

ALTER TABLE events ENABLE ROW LEVEL SECURITY;
