-- Apply explicitly as database owner. NOT part of sporting schema initialization.
-- Supabase already owns auth.users. No passwords are stored by this application.
BEGIN;
CREATE SCHEMA IF NOT EXISTS portal;
REVOKE ALL ON SCHEMA portal FROM PUBLIC, anon, authenticated;
CREATE TABLE IF NOT EXISTS portal.accounts (
    id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE RESTRICT,
    email text UNIQUE NOT NULL,
    display_name text NOT NULL,
    role text NOT NULL CHECK (role IN ('admin', 'scout')),
    active boolean NOT NULL DEFAULT true,
    revision integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS portal.account_audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    actor_id uuid NOT NULL REFERENCES portal.accounts(id),
    action text NOT NULL,
    target_id uuid NOT NULL REFERENCES portal.accounts(id)
);
ALTER TABLE portal.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal.account_audit ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA portal FROM PUBLIC, anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA portal FROM PUBLIC, anon, authenticated;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='portal_runtime') THEN
        CREATE ROLE portal_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END $$;
GRANT USAGE ON SCHEMA portal TO portal_runtime;
GRANT SELECT, INSERT, UPDATE ON portal.accounts TO portal_runtime;
GRANT SELECT, INSERT ON portal.account_audit TO portal_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA portal TO portal_runtime;
DROP POLICY IF EXISTS portal_backend_accounts ON portal.accounts;
CREATE POLICY portal_backend_accounts ON portal.accounts TO portal_runtime
    USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS portal_backend_audit ON portal.account_audit;
CREATE POLICY portal_backend_audit ON portal.account_audit TO portal_runtime
    USING (true) WITH CHECK (true);
COMMIT;
-- Set portal_runtime's password privately after applying. Never expose portal
-- in the Data API or grant these tables to anon/authenticated.
