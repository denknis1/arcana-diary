-- 009_daily_journal: stage 8.1 (spec 2026-11-27, owner decisions 51-53): the Card of the Day as a habit.
-- 1. daily_draws gets an owner of two kinds: a guest row has guest_id (the device cookie) and no user_id, as before,
--    an account row has user_id and no guest_id (one card per account and day on every device). The primary key
--    (guest_id, day) becomes a unique index on the same columns (NULLs never conflict), so the code of stage 4.2
--    keeps working on this table (its ON CONFLICT (guest_id, day) still finds the index: a rollback stays safe).
--    felt / note / noted_at: the evening mark "Did today's card show up in your day?" and a one-line note of at
--    most 280 characters (never sent to a model, never in an event).
-- 2. push_subscriptions: browser reminders (Web Push). One row per browser endpoint; the owner is an account or a
--    guest cookie, never both. Row level security on, no policies; migrate() revokes the browser roles (APP_TABLES).
-- 3. events: four more event names (spec §4 "События").
-- Every statement can run again (IF EXISTS / IF NOT EXISTS), as the review of 008 asked; migrate() runs the whole
-- file in one transaction, so the API never sees half of it. Until it has run, the new code meets a missing column
-- or table and answers 503 (db.py), never 500. daily_draws is small (7 days of guest rows before this stage).
ALTER TABLE daily_draws ADD COLUMN IF NOT EXISTS user_id uuid;
ALTER TABLE daily_draws ADD COLUMN IF NOT EXISTS felt text CHECK (felt IN ('yes', 'partly', 'no'));
ALTER TABLE daily_draws ADD COLUMN IF NOT EXISTS note text CHECK (char_length(note) <= 280);
ALTER TABLE daily_draws ADD COLUMN IF NOT EXISTS noted_at timestamptz;
ALTER TABLE daily_draws DROP CONSTRAINT IF EXISTS daily_draws_pkey;
ALTER TABLE daily_draws ALTER COLUMN guest_id DROP NOT NULL;
ALTER TABLE daily_draws DROP CONSTRAINT IF EXISTS daily_draws_one_owner;
ALTER TABLE daily_draws ADD CONSTRAINT daily_draws_one_owner CHECK ((guest_id IS NULL) <> (user_id IS NULL));
CREATE UNIQUE INDEX IF NOT EXISTS daily_draws_guest_day_key ON daily_draws (guest_id, day);
CREATE UNIQUE INDEX IF NOT EXISTS daily_draws_user_day_key ON daily_draws (user_id, day);
CREATE INDEX IF NOT EXISTS daily_draws_user_day_idx ON daily_draws (user_id, day DESC) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS daily_draws_day_idx ON daily_draws (day);

-- endpoint: the push service address the browser gave (https, an allowed push host: app/webpush.py).
-- p256dh, auth: the browser's keys for the message encryption (RFC 8291), base64url.
-- tz: an IANA zone name as resolved by the API. hour: the local hour of the reminder.
-- fails: failed deliveries in a row (3 delete the row). last_sent_day: the local day of the last reminder, or of
-- the day it was skipped because the card was already open, so there is at most one a day.
-- active_at: the guest's last Card of the Day visit (guest rows without one for 90 days are deleted).
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid,
    guest_id      uuid,
    endpoint      text NOT NULL UNIQUE CHECK (char_length(endpoint) <= 1024),
    p256dh        text NOT NULL CHECK (char_length(p256dh) <= 200),
    auth          text NOT NULL CHECK (char_length(auth) <= 50),
    lang          text NOT NULL CHECK (lang IN ('en', 'es')),
    tz            text NOT NULL CHECK (char_length(tz) <= 64),
    hour          smallint NOT NULL CHECK (hour BETWEEN 0 AND 23),
    fails         smallint NOT NULL DEFAULT 0 CHECK (fails >= 0),
    last_sent_day date,
    created_at    timestamptz NOT NULL,
    active_at     timestamptz NOT NULL,
    CONSTRAINT push_subscriptions_one_owner CHECK ((guest_id IS NULL) <> (user_id IS NULL))
);
CREATE INDEX IF NOT EXISTS push_subscriptions_user_idx ON push_subscriptions (user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS push_subscriptions_guest_idx ON push_subscriptions (guest_id) WHERE guest_id IS NOT NULL;
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;

ALTER TABLE events DROP CONSTRAINT IF EXISTS events_name_check;
ALTER TABLE events ADD CONSTRAINT events_name_check
    CHECK (name IN ('tool_view', 'draw_click', 'night_open', 'cards_revealed', 'reading_shown', 'save_click',
                    'signup_done', 'more_about_cards', 'outcome_answered', 'plus_view', 'remind_click',
                    'daily_felt', 'daily_calendar_view', 'push_enabled', 'push_click'));
