-- Apply as owner. Separate read-only credential for the admin COMET module.
BEGIN;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='comet_reader') THEN
        CREATE ROLE comet_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END $$;
GRANT USAGE ON SCHEMA public TO comet_reader;
GRANT SELECT ON public.actuaciones_arqueros, public.actuaciones_jugadores,
    public.competiciones, public.competidores, public.jugadores, public.partidos,
    public.partidos_fases, public.posiciones, public.equipos TO comet_reader;
ALTER ROLE comet_reader SET default_transaction_read_only=on;
-- SELECT grants alone do not expose rows when the sporting tables use RLS.
-- Only the dedicated backend reader receives this policy; existing policies stay.
DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'actuaciones_arqueros', 'actuaciones_jugadores', 'competiciones',
        'competidores', 'jugadores', 'partidos', 'partidos_fases', 'posiciones', 'equipos'
    ] LOOP
        EXECUTE format('DROP POLICY IF EXISTS portal_comet_read ON public.%I', table_name);
        EXECUTE format('CREATE POLICY portal_comet_read ON public.%I FOR SELECT TO comet_reader USING (true)', table_name);
    END LOOP;
END $$;
COMMIT;
-- Set password privately. No grants are added to anon/authenticated or scouting_runtime.
