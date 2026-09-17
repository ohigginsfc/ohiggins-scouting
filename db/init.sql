CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    birth_date DATE NULL,
    nationality TEXT NULL,
    position TEXT NULL,
    current_team TEXT NULL,
    preferred_foot TEXT NULL,
    height_cm NUMERIC NULL,
    image_path TEXT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scouting_reports (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_name TEXT NULL,
    scout_name TEXT NULL,
    report_date DATE NULL,
    competition TEXT NULL,
    match_observed TEXT NULL,
    position_observed TEXT NULL,
    minutes_observed INTEGER NULL,
    summary TEXT NULL,
    strengths TEXT NULL,
    weaknesses TEXT NULL,
    recommendation TEXT NULL,
    rating NUMERIC NULL,
    video_url TEXT NULL,
    alternative_positions TEXT[] NULL,
    raw_payload JSONB NULL,
    is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
    hidden_at TIMESTAMPTZ NULL,
    hidden_by VARCHAR NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS objective_metrics (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    season TEXT NULL,
    competition TEXT NULL,
    metric_name TEXT NOT NULL,
    metric_value NUMERIC NULL,
    metric_unit TEXT NULL,
    raw_payload JSONB NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_players_normalized_name ON players (normalized_name);
CREATE INDEX IF NOT EXISTS idx_scouting_reports_player_id ON scouting_reports (player_id);
CREATE INDEX IF NOT EXISTS idx_scouting_reports_report_date ON scouting_reports (report_date);
CREATE INDEX IF NOT EXISTS idx_objective_metrics_player_id ON objective_metrics (player_id);
CREATE INDEX IF NOT EXISTS idx_objective_metrics_metric_name ON objective_metrics (metric_name);

CREATE TABLE IF NOT EXISTS report_attribute_ratings (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES scouting_reports(id) ON DELETE CASCADE,
    attribute_group TEXT NOT NULL,
    attribute_name TEXT NOT NULL,
    rating NUMERIC(4,2) NOT NULL,
    max_rating NUMERIC(4,2) NOT NULL DEFAULT 5,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT now(),
    CONSTRAINT chk_report_attr_rating_bounds CHECK (max_rating > 0 AND rating >= 0 AND rating <= max_rating)
);

CREATE INDEX IF NOT EXISTS idx_report_attr_ratings_report_id ON report_attribute_ratings (report_id);
CREATE INDEX IF NOT EXISTS idx_report_attr_ratings_group ON report_attribute_ratings (attribute_group);
CREATE INDEX IF NOT EXISTS idx_report_attr_ratings_name ON report_attribute_ratings (attribute_name);

-- Migración ligera si la base ya existía sin estas columnas (idempotente en PG 11+)
ALTER TABLE players ADD COLUMN IF NOT EXISTS preferred_foot TEXT NULL;
ALTER TABLE players ADD COLUMN IF NOT EXISTS height_cm NUMERIC NULL;
ALTER TABLE scouting_reports ADD COLUMN IF NOT EXISTS video_url TEXT NULL;
ALTER TABLE players ADD COLUMN IF NOT EXISTS image_path TEXT NULL;
ALTER TABLE scouting_reports ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE scouting_reports ADD COLUMN IF NOT EXISTS hidden_at TIMESTAMPTZ NULL;
ALTER TABLE scouting_reports ADD COLUMN IF NOT EXISTS hidden_by VARCHAR NULL;

-- Sofascore / importación por lotes
CREATE TABLE IF NOT EXISTS data_import_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    country TEXT NOT NULL,
    division TEXT NOT NULL,
    competition TEXT NOT NULL,
    season TEXT NOT NULL,
    source_file TEXT NOT NULL,
    scraped_at TIMESTAMPTZ NULL,
    status TEXT NOT NULL DEFAULT 'running',
    stats JSONB NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_import_batches_scope
    ON data_import_batches (provider, country, division, season);

CREATE TABLE IF NOT EXISTS player_external_ids (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    external_id TEXT NOT NULL,
    external_name TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (provider, external_id)
);

CREATE INDEX IF NOT EXISTS idx_player_external_ids_player
    ON player_external_ids (player_id);

CREATE TABLE IF NOT EXISTS external_competitions (
    id SERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    country TEXT NOT NULL,
    division TEXT NOT NULL,
    competition TEXT NOT NULL,
    tournament_id INTEGER NOT NULL,
    season_id INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT true,
    UNIQUE (provider, tournament_id, season_id)
);

ALTER TABLE objective_metrics
    ADD COLUMN IF NOT EXISTS import_batch_id UUID NULL
    REFERENCES data_import_batches(id) ON DELETE SET NULL;

ALTER TABLE objective_metrics
    ADD COLUMN IF NOT EXISTS source_type TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_objective_metrics_import_batch
    ON objective_metrics (import_batch_id);

CREATE INDEX IF NOT EXISTS idx_objective_metrics_source_type
    ON objective_metrics (source_type);

CREATE INDEX IF NOT EXISTS idx_objective_metrics_source_type_season
    ON objective_metrics (source_type, season);

INSERT INTO external_competitions (
    provider, country, division, competition, tournament_id, season_id, is_active
)
VALUES
    ('sofascore', 'cl', 'primera', 'Primera División Chile', 11653, 88493, true),
    ('sofascore', 'cl', 'segunda', 'Liga de Ascenso Chile', 1240, 89007, true),
    ('sofascore', 'ar', 'primera', 'Liga Profesional Argentina', 155, 87913, true),
    ('sofascore', 'ar', 'segunda', 'Primera Nacional Argentina', 703, 87940, true),
    ('sofascore', 'uy', 'primera', 'Liga AUF Uruguay', 278, 89288, true),
    ('sofascore', 'uy', 'segunda', 'Segunda División Uruguay', 1908, 91195, true)
ON CONFLICT (provider, tournament_id, season_id) DO UPDATE SET
    country = EXCLUDED.country,
    division = EXCLUDED.division,
    competition = EXCLUDED.competition,
    is_active = true;
