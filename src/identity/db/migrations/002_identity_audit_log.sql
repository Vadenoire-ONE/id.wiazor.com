-- ============================================================================
-- 002_identity_audit_log.sql — Аудит-лог Identity-домена
-- Дата: 2025-06 (TD-1: Расщепление аудит-лога Identity ↔ RECON)
-- ============================================================================

-- ── 1. Таблица аудит-лога ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    action      TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id   TEXT NOT NULL,
    user_id     TEXT,
    details     JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Запрет UPDATE/DELETE на аудит-логе (append-only)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'identity_audit_log_immutable'
    ) THEN
        CREATE OR REPLACE FUNCTION prevent_identity_audit_mutation()
        RETURNS TRIGGER AS $fn$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only: UPDATE/DELETE forbidden';
        END;
        $fn$ LANGUAGE plpgsql;

        CREATE TRIGGER identity_audit_log_immutable
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION prevent_identity_audit_mutation();
    END IF;
END
$$;

-- ── 2. Индексы ──────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_identity_audit_action
    ON audit_log (action);

CREATE INDEX IF NOT EXISTS idx_identity_audit_entity
    ON audit_log (entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_identity_audit_created_at
    ON audit_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_identity_audit_user_id
    ON audit_log (user_id) WHERE user_id IS NOT NULL;
