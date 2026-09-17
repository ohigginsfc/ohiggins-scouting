-- Sofascore: lotes de importación, IDs externos, catálogo de competiciones.

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

CREATE INDEX IF NOT EXISTS idx_objective_metrics_import_batch
    ON objective_metrics (import_batch_id);

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
