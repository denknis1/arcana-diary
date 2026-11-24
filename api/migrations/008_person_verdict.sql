-- 008_person_verdict: stage 4.8 (spec 2026-11-24, owner decision 48). A yes/no question about another person
-- (guard group redirect_person) now gets the cards' verdict, so the verdict is allowed for that group too; health,
-- pregnancy, death, courts and safety (redirect_topic) stay without one. Only the CHECK constraint changes: the old
-- list plus 'redirect_person', so every existing row fits (person readings saved before have no verdict). Re-adding
-- it checks the existing rows under an ACCESS EXCLUSIVE lock on readings; the check is a cheap scan of the table.
ALTER TABLE readings DROP CONSTRAINT readings_verdict_allowed;
ALTER TABLE readings ADD CONSTRAINT readings_verdict_allowed
    CHECK (verdict IS NULL OR (kind = 'yes_no' AND guard_group IN ('ok', 'redirect_money', 'redirect_person')));
