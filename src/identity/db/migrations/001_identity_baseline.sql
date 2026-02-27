-- ============================================================================
-- Identity Domain — Baseline Schema (idempotent)
-- Version: 001
-- Date: 2025-07-15
--
-- Таблицы домена Identity (Domain A):
--   users, organizations, org_users
--
-- Этап 3, шаг 3.1: Identity выделен в отдельный сервис с собственной БД.
-- Этот файл содержит РЕАЛЬНЫЕ CREATE TABLE для Identity PostgreSQL.
-- При запуске в монолитном режиме (общая БД с RECON) — всё идемпотентно
-- (IF NOT EXISTS) и безопасно для повторного выполнения.
--
-- References:
--   - [RECON TZ: Section 3.1] User and Organization
--   - [change.md: Этап 2, шаг 2.4]
--   - [change.md: Этап 3, шаг 3.1]
-- ============================================================================

-- Расширение для генерации UUID v4
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- 1. USERS — Физические лица (ФЛ)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name     VARCHAR(255) NOT NULL,
    inn           VARCHAR(12) NOT NULL UNIQUE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    phone         VARCHAR(30) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'verified', 'blocked')),
    role          VARCHAR(20) NOT NULL DEFAULT 'viewer'
                  CHECK (role IN ('admin', 'director', 'accountant', 'viewer')),
    verification  JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 2. ORGANIZATIONS — Юридические лица
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organizations (
    org_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name       VARCHAR(512) NOT NULL,
    inn        VARCHAR(12) NOT NULL,
    ogrn       VARCHAR(15),
    email      VARCHAR(255),
    phone      VARCHAR(30),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 3. ORG_USERS — Связь пользователь ↔ организация (many-to-many)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS org_users (
    org_id   UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    user_id  UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role     VARCHAR(20) NOT NULL DEFAULT 'accountant'
             CHECK (role IN ('director', 'accountant', 'agent')),
    status   VARCHAR(20) NOT NULL DEFAULT 'pending'
             CHECK (status IN ('approved', 'pending')),
    PRIMARY KEY (org_id, user_id)
);

-- ---------------------------------------------------------------------------
-- Индексы
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_inn   ON users(inn);
CREATE INDEX IF NOT EXISTS idx_org_users_user_id ON org_users(user_id);

-- ============================================================================
-- Будущие расширения Identity-домена:
--   • Таблица email_confirmations (коды подтверждения)
--   • Таблица refresh_tokens (для отзыва токенов)
--   • Таблица verification_records (ЭЦП / платёж)
-- ============================================================================
