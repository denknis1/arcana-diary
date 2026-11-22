-- 005_request_ids: stage 4.5 (spec 2026-11-20 §5): one request, one reading. The site sends a request number
-- (UUID v4) with every draw and every follow-up and sends the same number again when a request got no answer at
-- all; the API then finds what it already made for that number instead of making a second one.
-- Additive only: two nullable columns without a default (a catalog-only change, existing rows are not rewritten)
-- and unique indexes in which NULL never conflicts, so every existing row fits and the build cannot fail. The
-- build holds a short write lock; the tables are small before launch. Both tables already have row level
-- security on and are in APP_TABLES (migrate() revokes the browser roles), so nothing else is needed.
ALTER TABLE readings ADD COLUMN request_id uuid;
ALTER TABLE followups ADD COLUMN request_id uuid;
-- the owner of a reading is its account when it has one, otherwise the device's guest (stage 4.3 §6)
CREATE UNIQUE INDEX readings_user_request_idx ON readings (user_id, request_id)
    WHERE request_id IS NOT NULL AND user_id IS NOT NULL;
CREATE UNIQUE INDEX readings_guest_request_idx ON readings (guest_id, request_id)
    WHERE request_id IS NOT NULL AND user_id IS NULL;
ALTER TABLE followups ADD CONSTRAINT followups_reading_request_key UNIQUE (reading_id, request_id);
