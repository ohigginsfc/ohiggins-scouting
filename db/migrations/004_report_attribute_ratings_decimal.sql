-- Escala subjetiva 0–5 con dos decimales (cuartos de punto).

CREATE TABLE IF NOT EXISTS report_attribute_ratings (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES scouting_reports(id) ON DELETE CASCADE,
    attribute_group TEXT NOT NULL,
    attribute_name TEXT NOT NULL,
    rating NUMERIC(4,2) NOT NULL,
    max_rating NUMERIC(4,2) NOT NULL DEFAULT 5,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_report_attr_ratings_report_id ON report_attribute_ratings (report_id);
CREATE INDEX IF NOT EXISTS idx_report_attr_ratings_group ON report_attribute_ratings (attribute_group);
CREATE INDEX IF NOT EXISTS idx_report_attr_ratings_name ON report_attribute_ratings (attribute_name);

ALTER TABLE report_attribute_ratings
    ALTER COLUMN rating TYPE NUMERIC(4,2) USING rating::NUMERIC(4,2);

ALTER TABLE report_attribute_ratings
    ALTER COLUMN max_rating TYPE NUMERIC(4,2) USING max_rating::NUMERIC(4,2);

ALTER TABLE report_attribute_ratings
    ALTER COLUMN max_rating SET DEFAULT 5;

ALTER TABLE report_attribute_ratings
    DROP CONSTRAINT IF EXISTS chk_report_attr_rating_bounds;

ALTER TABLE report_attribute_ratings
    ADD CONSTRAINT chk_report_attr_rating_bounds
    CHECK (max_rating > 0 AND rating >= 0 AND rating <= max_rating);
