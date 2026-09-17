-- Campos ampliados de ficha del jugador.

ALTER TABLE players ADD COLUMN IF NOT EXISTS preferred_foot TEXT NULL;
ALTER TABLE players ADD COLUMN IF NOT EXISTS height_cm NUMERIC NULL;
ALTER TABLE players ADD COLUMN IF NOT EXISTS birth_date DATE NULL;

ALTER TABLE scouting_reports ADD COLUMN IF NOT EXISTS video_url TEXT NULL;
