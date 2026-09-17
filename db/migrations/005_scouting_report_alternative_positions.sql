-- Posiciones alternativas observadas en el informe (scout).

ALTER TABLE scouting_reports
    ADD COLUMN IF NOT EXISTS alternative_positions TEXT[] NULL;
