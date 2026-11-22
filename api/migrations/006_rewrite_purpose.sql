-- 006_rewrite_purpose: stage 4.7 (spec 2026-11-22). The call that rewrites a Spanish section without gendered
-- forms for the reader is logged in llm_calls as purpose 'rewrite' (it counts toward DAILY_BUDGET_USD like any
-- reader call). Only the CHECK constraint changes: the old list plus 'rewrite', so every existing row fits and the
-- build cannot fail. Re-adding it checks the existing rows under a short write lock; llm_calls is small (no texts,
-- a few rows per reading). The table already has row level security on and is in APP_TABLES: nothing else changes.
ALTER TABLE llm_calls DROP CONSTRAINT llm_calls_purpose_check;
ALTER TABLE llm_calls ADD CONSTRAINT llm_calls_purpose_check
    CHECK (purpose IN ('reader', 'followup', 'daily', 'guard', 'rewrite'));
