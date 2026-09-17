-- Amplía processing_status para distinguir descarga vs importación PostgreSQL.
-- pending: descubierto / no descargado
-- downloaded: scrapado a checkpoint, pendiente de importar
-- processed: importado correctamente a PostgreSQL
-- failed / skipped: sin cambios de significado

ALTER TABLE sofascore_event_ingestion
    DROP CONSTRAINT IF EXISTS sofascore_event_ingestion_status_check;

ALTER TABLE sofascore_event_ingestion
    ADD CONSTRAINT sofascore_event_ingestion_status_check
        CHECK (
            processing_status IN (
                'pending',
                'downloaded',
                'processed',
                'failed',
                'skipped'
            )
        );
