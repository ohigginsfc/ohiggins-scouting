-- Ruta relativa de foto en players (no binario en BD).

ALTER TABLE players ADD COLUMN IF NOT EXISTS image_path TEXT NULL;
