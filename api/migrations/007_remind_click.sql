-- 007_remind_click: stage 4.4b (spec 2026-11-22 §7). The event counter accepts one more event, remind_click
-- ("Remind me tomorrow" under the Card of the Day). Only the CHECK constraint changes: the old list plus
-- 'remind_click', so every existing row fits. Re-adding it checks the existing rows under a short write lock
-- (events is small: one row per event, no texts). Row level security and APP_TABLES stay as they are.
ALTER TABLE events DROP CONSTRAINT events_name_check;
ALTER TABLE events ADD CONSTRAINT events_name_check
    CHECK (name IN ('tool_view', 'draw_click', 'night_open', 'cards_revealed', 'reading_shown', 'save_click',
                    'signup_done', 'more_about_cards', 'outcome_answered', 'plus_view', 'remind_click'));
