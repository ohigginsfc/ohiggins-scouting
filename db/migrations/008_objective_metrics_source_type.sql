-- 008: origen de métricas objetivas (demo vs sofascore)
-- Permite no confundir seed/demo con importación real de Sofascore.

ALTER TABLE objective_metrics
    ADD COLUMN IF NOT EXISTS source_type TEXT NULL;

COMMENT ON COLUMN objective_metrics.source_type IS
    'Origen de la fila: sofascore | demo | manual | other';

-- Datos importados vía lote Sofascore
UPDATE objective_metrics
SET source_type = 'sofascore'
WHERE source_type IS NULL
  AND import_batch_id IS NOT NULL;

-- Seed demo y fuentes legacy de demostración (sin lote de importación)
UPDATE objective_metrics
SET source_type = 'demo'
WHERE source_type IS NULL
  AND (
        source_name IN ('StatsDemo', 'examples_generated', 'DEMO')
        OR (
            source_name = 'Sofascore'
            AND import_batch_id IS NULL
        )
      );

CREATE INDEX IF NOT EXISTS idx_objective_metrics_source_type
    ON objective_metrics (source_type);

CREATE INDEX IF NOT EXISTS idx_objective_metrics_source_type_season
    ON objective_metrics (source_type, season);
