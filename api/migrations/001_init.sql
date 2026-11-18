-- 001_init: stage 4.2 schema (spec §4.3, §8). Access only from the API with the server connection string:
-- row level security is enabled on every table and no policies are created, so browser access is closed.

CREATE TABLE readings (
    id                uuid PRIMARY KEY,
    guest_id          uuid NOT NULL,
    user_id           uuid,
    lang              text NOT NULL CHECK (lang IN ('en', 'es')),
    kind              text NOT NULL CHECK (kind IN ('one', 'three', 'yes_no', 'card_page')),
    question          text CHECK (char_length(question) <= 500),
    topic             text CHECK (topic IN ('love', 'work', 'self', 'decision', 'general')),
    situation         text CHECK (situation IN ('single', 'relationship', 'after_breakup', 'complicated')),
    source_card_id    text,
    cards             jsonb NOT NULL,
    seed              text NOT NULL,
    verdict           text CHECK (verdict IN ('yes', 'no', 'unclear')),
    guard_group       text NOT NULL
                      CHECK (guard_group IN ('ok', 'redirect_money', 'redirect_topic', 'redirect_person')),
    answer            jsonb,
    answer_shown      text CHECK (answer_shown IN ('model', 'fallback', 'crisis')),
    model             text,
    prompt_version    text,
    retries           smallint NOT NULL DEFAULT 0 CHECK (retries BETWEEN 0 AND 2),
    -- §10.2: follow-up requests for this reading, crisis answers, refusals and failures included
    followup_attempts smallint NOT NULL DEFAULT 0 CHECK (followup_attempts BETWEEN 0 AND 8),
    stream_started_at timestamptz,
    created_at        timestamptz NOT NULL,
    expires_at        timestamptz,
    -- §8.1: a verdict only for yes/no, and never for health, pregnancy, death, courts, safety or another person
    CONSTRAINT readings_verdict_allowed
        CHECK (verdict IS NULL OR (kind = 'yes_no' AND guard_group IN ('ok', 'redirect_money')))
);
CREATE INDEX readings_guest_created_idx ON readings (guest_id, created_at DESC);
CREATE INDEX readings_expires_idx ON readings (expires_at) WHERE expires_at IS NOT NULL;

-- counted = false: the answer was cut or replaced by the card base line; it does not use a free follow-up (§9.4).
-- paid_day: a follow-up after the two free ones took a reading of the guest's day (usage 'guest:<uuid>', §10.1);
-- a failed one gives it back. NULL — a free follow-up.
CREATE TABLE followups (
    id          uuid PRIMARY KEY,
    reading_id  uuid NOT NULL REFERENCES readings (id) ON DELETE CASCADE,
    n           smallint NOT NULL CHECK (n BETWEEN 1 AND 8),
    question    text NOT NULL CHECK (char_length(question) <= 500),
    guard_group text NOT NULL DEFAULT 'ok'
                CHECK (guard_group IN ('ok', 'redirect_money', 'redirect_topic', 'redirect_person')),
    answer      jsonb,
    model       text,
    counted     boolean NOT NULL DEFAULT true,
    paid_day    date,
    created_at  timestamptz NOT NULL,
    UNIQUE (reading_id, n)
);

CREATE TABLE daily_cache (
    card_id        text NOT NULL,
    reversed       boolean NOT NULL,
    lang           text NOT NULL CHECK (lang IN ('en', 'es')),
    day            date NOT NULL,
    text           text NOT NULL,
    model          text,
    prompt_version text,
    created_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (card_id, reversed, lang, day)
);

CREATE TABLE daily_draws (
    guest_id uuid NOT NULL,
    day      date NOT NULL,
    card_id  text NOT NULL,
    reversed boolean NOT NULL,
    PRIMARY KEY (guest_id, day)
);

-- subject: 'guest:<uuid>' (day = the guest's local day; readings and paid follow-ups), 'ip:<sha256>' (readings),
-- 'ipf:<sha256>' (follow-ups) or 'ipg:<sha256>' (question checks by the model on reading creation); for the
-- addresses day = UTC day of the salt
CREATE TABLE usage (
    subject text NOT NULL,
    day     date NOT NULL,
    count   integer NOT NULL DEFAULT 0 CHECK (count >= 0),
    PRIMARY KEY (subject, day)
);
CREATE INDEX usage_day_idx ON usage (day);

-- counts only, no question text (§3.4); source: where the group came from, so timeouts and refusals are counted
CREATE TABLE guard_events (
    day         date NOT NULL,
    lang        text NOT NULL CHECK (lang IN ('en', 'es')),
    guard_group text NOT NULL
                CHECK (guard_group IN ('ok', 'redirect_money', 'redirect_topic', 'redirect_person', 'crisis')),
    source      text NOT NULL
                CHECK (source IN ('terms', 'model', 'timeout', 'refusal', 'error', 'invalid', 'reader', 'budget')),
    count       integer NOT NULL DEFAULT 0,
    PRIMARY KEY (day, lang, guard_group, source)
);

-- no texts (§5.4); reading_id is not a foreign key: the log outlives expired guest readings
CREATE TABLE llm_calls (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reading_id       uuid,
    purpose          text NOT NULL CHECK (purpose IN ('reader', 'followup', 'daily', 'guard')),
    model            text NOT NULL,
    prompt_version   text,
    ms_first_token   integer,
    ms_total         integer,
    tokens_in        integer,
    tokens_out       integer,
    cost_usd         numeric(12, 6),
    stop_reason      text,
    refusal_category text,
    created_at       timestamptz NOT NULL
);
CREATE INDEX llm_calls_created_idx ON llm_calls (created_at);

ALTER TABLE readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE followups ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_draws ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE guard_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_calls ENABLE ROW LEVEL SECURITY;
