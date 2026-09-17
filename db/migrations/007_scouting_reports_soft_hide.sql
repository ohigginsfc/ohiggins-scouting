-- Soft-hide for scouting reports (idempotent).
-- Hidden reports remain in PostgreSQL; permanent delete is a separate action.

ALTER TABLE scouting_reports
    ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE scouting_reports
    ADD COLUMN IF NOT EXISTS hidden_at TIMESTAMPTZ NULL;

ALTER TABLE scouting_reports
    ADD COLUMN IF NOT EXISTS hidden_by VARCHAR NULL;

CREATE INDEX IF NOT EXISTS idx_scouting_reports_is_hidden
    ON scouting_reports (is_hidden)
    WHERE is_hidden = TRUE;
