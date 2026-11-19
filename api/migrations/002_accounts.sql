-- 002_accounts: stage 4.3 (spec 2026-11-19 §9): the diary fields of a reading, one-time claim tokens, account
-- profiles, the Plus waitlist and deleted accounts. As in 001: row level security on, no policies, the browser roles get no rights
-- (migrate() revokes them), so only the API reads these tables.

-- outcome: the person's own mark "did it come true?" (never sent to a model)
-- note: a private note, at most 1000 characters (never sent to a model)
ALTER TABLE readings ADD COLUMN outcome text CHECK (outcome IN ('yes', 'partly', 'no'));
ALTER TABLE readings ADD COLUMN outcome_at timestamptz;
ALTER TABLE readings ADD COLUMN note text CHECK (char_length(note) <= 1000);
ALTER TABLE readings ADD COLUMN note_updated_at timestamptz;
CREATE INDEX readings_user_created_idx ON readings (user_id, created_at DESC);

-- a claim token moves one guest reading into an account from any device: only the sha256 of the token is kept
CREATE TABLE claim_tokens (
    token_hash text PRIMARY KEY,
    reading_id uuid NOT NULL REFERENCES readings (id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    used_at    timestamptz
);
CREATE INDEX claim_tokens_reading_idx ON claim_tokens (reading_id);
CREATE INDEX claim_tokens_expires_idx ON claim_tokens (expires_at);

-- one row per account, made on first use: the e-mail stays in Supabase (it comes with every token)
CREATE TABLE profiles (
    user_id           uuid PRIMARY KEY,
    created_at        timestamptz NOT NULL,
    reminders_consent boolean NOT NULL DEFAULT false,
    consent_at        timestamptz
);

-- "tell me when Plus opens"; the e-mail is stored in lower case
CREATE TABLE plus_waitlist (
    email      text PRIMARY KEY CHECK (email = lower(email) AND char_length(email) <= 254),
    lang       text NOT NULL CHECK (lang IN ('en', 'es')),
    user_id    uuid,
    created_at timestamptz NOT NULL
);
CREATE INDEX plus_waitlist_user_idx ON plus_waitlist (user_id) WHERE user_id IS NOT NULL;

-- an access token outlives the account it was issued for (until its exp): such tokens are refused while the row
-- lives; the cleanup forgets rows older than the longest token life
CREATE TABLE deleted_accounts (
    user_id    uuid PRIMARY KEY,
    deleted_at timestamptz NOT NULL
);

ALTER TABLE claim_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE plus_waitlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE deleted_accounts ENABLE ROW LEVEL SECURITY;
