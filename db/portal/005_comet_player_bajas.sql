-- Apply explicitly as database owner AFTER review. NOT applied by the portal or by CI.
-- Bajas de jugadores en el seguimiento COMET: un administrador saca a un jugador del plantel vigente (por ejemplo,
-- una sub-20 o menor que deja el club). No toca COMET ni borra datos: COMET se lee con comet_reader (solo lectura)
-- y la baja solo se guarda aquí, en el esquema privado `portal`. Es reversible: reincorporar la desactiva.
-- Requires 001_accounts.sql (schema portal, table portal.accounts, role portal_runtime).
BEGIN;

CREATE TABLE IF NOT EXISTS portal.comet_player_bajas (
    -- personid como texto, igual que portal.comet_player_marks: no depende del tipo de la columna en COMET.
    personid text PRIMARY KEY CHECK (length(personid) BETWEEN 1 AND 40),
    active boolean NOT NULL DEFAULT true,
    reason text NOT NULL CHECK (reason IN ('dejo_club', 'cedido', 'transferido', 'otro')),
    effective_on date NOT NULL,
    note text NOT NULL DEFAULT '' CHECK (length(note) <= 500),
    created_by uuid NOT NULL REFERENCES portal.accounts(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid NOT NULL REFERENCES portal.accounts(id),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS comet_player_bajas_active_idx ON portal.comet_player_bajas (personid) WHERE active;

ALTER TABLE portal.comet_player_bajas ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON portal.comet_player_bajas FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON portal.comet_player_bajas TO portal_runtime;

DROP POLICY IF EXISTS portal_backend_comet_bajas ON portal.comet_player_bajas;
CREATE POLICY portal_backend_comet_bajas ON portal.comet_player_bajas TO portal_runtime
    USING (true) WITH CHECK (true);
COMMIT;
-- No se concede nada a anon/authenticated ni a scouting_runtime/comet_reader, y no hay DELETE: "se desactiva, no se borra".
-- Solo se guarda el identificador del jugador, el motivo, la fecha y una nota; los datos del jugador siguen en COMET.
