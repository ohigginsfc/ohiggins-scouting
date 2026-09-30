-- Apply explicitly as database owner AFTER review. NOT applied by the portal or by CI.
-- Seguimiento deportivo de COMET: configuración de reglas y alertas, marcas de jugadores y
-- períodos de selección. Vive en el esquema privado `portal` (nunca en `public`): el rol
-- comet_reader es de solo lectura y no puede guardar configuración.
-- Requires 001_accounts.sql (schema portal, table portal.accounts, role portal_runtime).
BEGIN;

-- Reglas y alertas configurables. `confirmed` indica que el club aprobó ese valor;
-- mientras sea false la interfaz lo presenta como supuesto pendiente.
CREATE TABLE IF NOT EXISTS portal.comet_settings (
    key text PRIMARY KEY CHECK (length(key) BETWEEN 1 AND 64),
    value jsonb NOT NULL,
    confirmed boolean NOT NULL DEFAULT false,
    updated_by uuid NOT NULL REFERENCES portal.accounts(id),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Jugadores proyectados o de selección. personid se guarda como texto para no depender
-- del tipo de la columna en COMET. No se borra: se desactiva y queda el historial.
CREATE TABLE IF NOT EXISTS portal.comet_player_marks (
    personid text NOT NULL CHECK (length(personid) BETWEEN 1 AND 40),
    mark text NOT NULL CHECK (mark IN ('proyectado', 'seleccion')),
    active boolean NOT NULL DEFAULT true,
    note text NOT NULL DEFAULT '' CHECK (length(note) <= 500),
    updated_by uuid NOT NULL REFERENCES portal.accounts(id),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (personid, mark)
);

-- Períodos de microciclo de selección, Sudamericano o Mundial de un jugador.
CREATE TABLE IF NOT EXISTS portal.comet_selection_periods (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    personid text NOT NULL CHECK (length(personid) BETWEEN 1 AND 40),
    kind text NOT NULL CHECK (kind IN ('microciclo', 'sudamericano', 'mundial')),
    starts_on date NOT NULL,
    ends_on date NOT NULL,
    note text NOT NULL DEFAULT '' CHECK (length(note) <= 500),
    active boolean NOT NULL DEFAULT true,
    created_by uuid NOT NULL REFERENCES portal.accounts(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    retired_by uuid REFERENCES portal.accounts(id),
    retired_at timestamptz,
    CHECK (ends_on >= starts_on)
);
CREATE INDEX IF NOT EXISTS comet_selection_periods_person_idx
    ON portal.comet_selection_periods (personid) WHERE active;

ALTER TABLE portal.comet_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal.comet_player_marks ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal.comet_selection_periods ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON portal.comet_settings, portal.comet_player_marks, portal.comet_selection_periods
    FROM PUBLIC, anon, authenticated;

GRANT SELECT, INSERT, UPDATE ON portal.comet_settings TO portal_runtime;
GRANT SELECT, INSERT, UPDATE ON portal.comet_player_marks TO portal_runtime;
GRANT SELECT, INSERT, UPDATE ON portal.comet_selection_periods TO portal_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA portal TO portal_runtime;

DROP POLICY IF EXISTS portal_backend_comet_settings ON portal.comet_settings;
CREATE POLICY portal_backend_comet_settings ON portal.comet_settings TO portal_runtime
    USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS portal_backend_comet_marks ON portal.comet_player_marks;
CREATE POLICY portal_backend_comet_marks ON portal.comet_player_marks TO portal_runtime
    USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS portal_backend_comet_periods ON portal.comet_selection_periods;
CREATE POLICY portal_backend_comet_periods ON portal.comet_selection_periods TO portal_runtime
    USING (true) WITH CHECK (true);
COMMIT;
-- No se concede nada a anon/authenticated ni a scouting_runtime/comet_reader, y no hay DELETE.
-- Los datos de jugadores (menores) no salen de Supabase: solo se guardan sus identificadores.
