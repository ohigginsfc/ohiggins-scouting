-- Ejecutar como administrador de PostgreSQL. No concede escritura ni acceso al rol scout.
BEGIN;
DO $$
BEGIN
    IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.eventos_partido'::regclass) THEN
        RAISE EXCEPTION 'eventos_partido requiere RLS habilitado antes de ampliar la lectura';
    END IF;
END $$;
GRANT SELECT ON public.eventos_partido TO comet_reader;
DROP POLICY IF EXISTS portal_comet_events_read ON public.eventos_partido;
CREATE POLICY portal_comet_events_read ON public.eventos_partido
    FOR SELECT TO comet_reader
    USING (EXISTS (
        SELECT 1 FROM public.partidos p
        WHERE p.matchid = eventos_partido.matchid
          AND (p.hometeam = 40010 OR p.awayteam = 40010)
    ));
-- Conserva las políticas y el estado de RLS existentes; no modifica otros roles.
COMMIT;
