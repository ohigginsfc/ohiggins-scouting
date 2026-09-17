-- Estado de ingestión incremental por evento Sofascore.

CREATE TABLE IF NOT EXISTS sofascore_event_ingestion (
    id SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL DEFAULT 'Sofascore',
    country TEXT NOT NULL,
    division TEXT NOT NULL,
    competition TEXT NOT NULL,
    season INTEGER NOT NULL,
    event_id BIGINT NOT NULL,
    home_team TEXT,
    away_team TEXT,
    event_date TIMESTAMP NULL,
    status TEXT,
    has_lineups BOOLEAN,
    has_xg BOOLEAN,
    checksum TEXT,
    processing_status TEXT NOT NULL DEFAULT 'pending',
    scraped_at TIMESTAMP NULL,
    import_batch_id UUID NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT sofascore_event_ingestion_status_check
        CHECK (processing_status IN ('pending', 'processed', 'failed', 'skipped')),
    CONSTRAINT sofascore_event_ingestion_unique_event
        UNIQUE (source_name, competition, season, event_id)
);

CREATE INDEX IF NOT EXISTS idx_sofascore_event_ingestion_scope
    ON sofascore_event_ingestion (country, division, competition, season);

CREATE INDEX IF NOT EXISTS idx_sofascore_event_ingestion_status
    ON sofascore_event_ingestion (processing_status);
