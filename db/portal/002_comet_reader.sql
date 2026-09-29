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
COMMIT;
-- Set password privately. No grants are added to anon/authenticated or scouting_runtime.
