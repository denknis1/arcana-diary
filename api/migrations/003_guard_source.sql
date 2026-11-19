-- 003_guard_source: stage 4.3 final review I2. Where the question check's group came from (GuardResult.source:
-- terms, model, timeout, error, invalid, refusal, budget); NULL for a reading without a question and for rows made
-- before this migration. A timeout or an error stores guard_group 'ok' (fail open, guard.py), so the reader memory
-- (repo.topic_history) takes only questions the check really classified ('terms' or 'model').
-- Nullable, no default: a catalog-only change on the live table, existing rows are not rewritten. readings already
-- has row level security on and is in APP_TABLES (migrate() revokes the browser roles), so nothing else is needed.
ALTER TABLE readings ADD COLUMN guard_source text;
